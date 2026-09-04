"""Business logic for the priced therapy booking + Razorpay payment flow."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from bson.errors import InvalidId

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.dependencies.auth import ActorContext
from app.models.base import utcnow
from app.models.enums import (
    ActivityAction,
    BookingStatus,
    EquipmentOwner,
    Gender,
    NotificationType,
    PaymentStatus,
    ServiceCategory,
    Shift,
    SlotType,
)
from app.models.pricing_settings import PricingSettings
from app.models.therapist_slot import TherapistSlot
from app.models.therapy_booking import TherapyBooking
from app.models.therapy_equipment import BookedEquipment, TherapyEquipment
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.therapy_booking import PaymentVerifyRequest, PricingQuoteRequest, TherapyBookingCreate
from app.services import pricing_service
from app.services.activity_service import activity_service
from app.services.commission_service import commission_service
from app.services.email_service import email_service
from app.services.notification_service import notification_service
from app.services.razorpay_service import razorpay_service
from app.utils.references import generate_reference

# Which UserType slug(s) may be assigned to each service category.
ASSIGNABLE_USER_TYPES = {
    ServiceCategory.PHYSIOTHERAPY: {"physiotherapist"},
    ServiceCategory.YOGA_THERAPY: {"yoga_therapist"},
    ServiceCategory.MASSAGE_THERAPY: {"massage_therapist"},
    # No dedicated "rehab therapist" type is seeded; physiotherapists cover it.
    ServiceCategory.HOME_REHABILITATION: {"physiotherapist"},
}

TERMINAL_STATUSES = {BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.REJECTED}
ASSIGNABLE_STATUSES = {BookingStatus.APPROVED, BookingStatus.IN_PROGRESS}


class TherapyBookingService:
    def __init__(self) -> None:
        self.repo: BaseRepository[TherapyBooking] = BaseRepository(TherapyBooking)
        self.repo.search_fields = ("reference", "patient_name", "contact_phone")

    # ---- Pricing --------------------------------------------------------

    @staticmethod
    async def get_rates() -> PricingSettings:
        """Return the current admin-configured pricing/refund rates (singleton, created on first use)."""
        rates = await PricingSettings.find_one({})
        if rates is None:
            rates = PricingSettings()
            await rates.insert()
        return rates

    @staticmethod
    async def resolve_equipment(
        equipment_ids: List[str],
        service_category: ServiceCategory,
        therapist_id: Optional[str] = None,
    ) -> List[BookedEquipment]:
        """Turn selected equipment ids into priced snapshots.

        Rejects anything that isn't offered for this booking: wrong service
        category, inactive, or another therapist's personal equipment.
        """
        if not equipment_ids:
            return []

        object_ids = []
        for eid in equipment_ids:
            try:
                object_ids.append(ObjectId(eid))
            except (InvalidId, TypeError):
                raise BadRequestException(f"Invalid equipment id: {eid}")

        items = await TherapyEquipment.find({"_id": {"$in": object_ids}}).to_list()
        found = {str(i.id): i for i in items}

        snapshots: List[BookedEquipment] = []
        for eid in equipment_ids:
            item = found.get(eid)
            if item is None:
                raise BadRequestException(f"Equipment not found: {eid}")
            if not item.is_active:
                raise BadRequestException(f"'{item.name}' is no longer available")
            if item.category != service_category:
                raise BadRequestException(
                    f"'{item.name}' is not available for {service_category.value.replace('_', ' ')}"
                )
            if item.owner_type == EquipmentOwner.THERAPIST and item.therapist_id != therapist_id:
                raise BadRequestException(
                    f"'{item.name}' belongs to a different therapist and can't be added to this booking"
                )
            snapshots.append(
                BookedEquipment(
                    equipment_id=str(item.id),
                    name=item.name,
                    charge=item.charge,
                    owner_type=item.owner_type.value,
                )
            )
        return snapshots

    @staticmethod
    async def compute_pricing(
        payload: TherapyBookingCreate | PricingQuoteRequest,
        equipment_items: Optional[List[BookedEquipment]] = None,
    ) -> pricing_service.PricingResult:
        rates = await TherapyBookingService.get_rates()

        if equipment_items is None:
            equipment_items = await TherapyBookingService.resolve_equipment(
                list(getattr(payload, "equipment_ids", []) or []),
                payload.service_category,
                getattr(payload, "therapist_id", None),
            )
        charges = [e.charge for e in equipment_items]

        if payload.service_category == ServiceCategory.MASSAGE_THERAPY:
            return pricing_service.price_massage_booking(
                massage_type=payload.massage_type,
                massage_duration_minutes=payload.massage_duration_minutes,
                equipment_charges=charges,
                rates=rates,
            )
        return pricing_service.price_visit_booking(
            service_category=payload.service_category,
            frequency_type=payload.frequency_type,
            daily_visits_per_day=payload.daily_visits_per_day,
            equipment=payload.equipment,
            equipment_charges=charges,
            rates=rates,
        )

    # ---- Therapist & slot resolution ---------------------------------------

    @staticmethod
    def _shift_for(start_time: str) -> Shift:
        """Bucket a 'HH:MM' start time into the patient-facing shift label."""
        hour = int(start_time.split(":")[0])
        if hour < 12:
            return Shift.MORNING
        if hour < 14:
            return Shift.NOON
        if hour < 17:
            return Shift.AFTERNOON
        return Shift.EVENING

    @staticmethod
    async def validate_therapist_for_booking(
        therapist_id: str,
        service_category: ServiceCategory,
        patient_gender: Optional[Gender],
    ) -> User:
        """Check a therapist may take this booking, before any money moves."""
        therapist = await User.get(therapist_id)
        if therapist is None or therapist.role != "therapist":
            raise BadRequestException("Selected therapist not found")
        if not therapist.is_active or therapist.verification_status != "approved":
            raise BadRequestException("This therapist is not currently accepting bookings")

        allowed = ASSIGNABLE_USER_TYPES.get(service_category, set())
        if therapist.user_type not in allowed:
            raise BadRequestException(
                f"{therapist.name} does not provide {service_category.value.replace('_', ' ')}"
            )

        if service_category == ServiceCategory.MASSAGE_THERAPY:
            wanted = patient_gender.value if patient_gender else None
            if not wanted or not therapist.gender or therapist.gender != wanted:
                raise BadRequestException(
                    "Massage therapy requires a therapist of the same gender as the patient (safety policy)"
                )
        return therapist

    async def _claim_slot(self, slot_id: str, therapist_id: str, patient_name: str, user_id: str) -> TherapistSlot:
        """Atomically take a free slot, or fail if someone else just took it."""
        try:
            oid = ObjectId(slot_id)
        except (InvalidId, TypeError):
            raise BadRequestException("Invalid slot id")

        slot = await TherapistSlot.get(slot_id)
        if slot is None:
            raise NotFoundException("Slot not found")
        if slot.therapist_id != therapist_id:
            raise BadRequestException("That slot belongs to a different therapist")
        if slot.slot_type != SlotType.HOME_VISIT:
            raise BadRequestException("That slot is not a home-visit slot")
        if slot.date < dt.date.today().isoformat():
            raise BadRequestException("That slot is in the past")

        result = await TherapistSlot.get_motor_collection().update_one(
            {"_id": oid, "is_booked": False},
            {
                "$set": {
                    "is_booked": True,
                    "booked_by_user_id": user_id,
                    "booked_by_patient_name": patient_name,
                    "updated_at": utcnow(),
                }
            },
        )
        if result.matched_count == 0:
            raise BadRequestException("That slot was just booked by someone else — please pick another")

        return await TherapistSlot.get(slot_id)

    async def _release_slot(self, booking: TherapyBooking) -> None:
        """Free the slot a cancelled/rejected booking was holding."""
        if not booking.slot_id:
            return
        try:
            oid = ObjectId(booking.slot_id)
        except (InvalidId, TypeError):
            return
        await TherapistSlot.get_motor_collection().update_one(
            {"_id": oid},
            {
                "$set": {
                    "is_booked": False,
                    "booked_by_user_id": None,
                    "booked_by_patient_name": None,
                    "therapy_booking_id": None,
                    "booking_reference": None,
                    "updated_at": utcnow(),
                }
            },
        )

    # ---- Create + payment -------------------------------------------------

    async def create_with_payment_order(
        self, payload: TherapyBookingCreate, patient_id: Optional[str]
    ) -> Tuple[TherapyBooking, Dict[str, Any]]:
        therapist: Optional[User] = None
        slot: Optional[TherapistSlot] = None

        # Therapist-first flow: validate the therapist, then take their slot.
        if payload.therapist_id:
            therapist = await self.validate_therapist_for_booking(
                payload.therapist_id, payload.service_category, payload.patient_gender
            )

        equipment_items = await self.resolve_equipment(
            payload.equipment_ids, payload.service_category, payload.therapist_id
        )
        pricing = await self.compute_pricing(payload, equipment_items=equipment_items)

        if payload.slot_id:
            slot = await self._claim_slot(
                payload.slot_id,
                payload.therapist_id,
                payload.patient_name,
                str(patient_id) if patient_id else "",
            )
            preferred_date = dt.date.fromisoformat(slot.date)
            shift = self._shift_for(slot.start_time)
            time_slot = f"{slot.start_time} - {slot.end_time}"
        else:
            preferred_date = payload.preferred_date
            shift = payload.shift
            time_slot = payload.time_slot

        booking = TherapyBooking(
            reference=generate_reference("THB"),
            patient_id=patient_id,
            patient_name=payload.patient_name,
            patient_age=payload.patient_age,
            patient_gender=payload.patient_gender,
            contact_phone=payload.contact_phone,
            contact_email=payload.contact_email,
            address=payload.address,
            city=payload.city,
            pincode=payload.pincode,
            service_category=payload.service_category,
            condition_notes=payload.condition_notes,
            preferred_date=preferred_date,
            shift=shift,
            time_slot=time_slot,
            session_duration_minutes=payload.session_duration_minutes,
            slot_id=payload.slot_id,
            equipment_items=equipment_items,
            assigned_staff_id=str(therapist.id) if therapist else None,
            assigned_staff_name=therapist.name if therapist else None,
            frequency_type=payload.frequency_type,
            daily_visits_per_day=payload.daily_visits_per_day,
            weekly_days_count=payload.weekly_days_count,
            package_duration=payload.package_duration,
            package_custom_months=payload.package_custom_months,
            equipment=payload.equipment,
            massage_type=payload.massage_type,
            massage_duration_minutes=payload.massage_duration_minutes,
            visit_fee=pricing.visit_fee,
            machine_charge=pricing.machine_charge,
            total_amount=pricing.total_amount,
            platform_fee_percent=pricing.platform_fee_percent,
            platform_fee_amount=pricing.platform_fee_amount,
            therapist_payout=pricing.therapist_payout,
        )
        await self.repo.create(booking)

        # Point the claimed slot back at the booking so cancelling can free it.
        if slot is not None:
            await TherapistSlot.get_motor_collection().update_one(
                {"_id": slot.id},
                {"$set": {"therapy_booking_id": str(booking.id), "booking_reference": booking.reference}},
            )

        order = await razorpay_service.create_order(
            amount_rupees=booking.total_amount,
            receipt=booking.reference,
            notes={"booking_id": str(booking.id), "service_category": booking.service_category.value},
        )
        booking.razorpay_order_id = order["id"]
        booking.touch()
        await booking.save()

        return booking, order

    async def verify_payment(self, booking_id: str, payload: PaymentVerifyRequest) -> TherapyBooking:
        booking = await self._get_or_404(booking_id)

        if booking.payment_status == PaymentStatus.PAID:
            return booking
        if booking.razorpay_order_id != payload.razorpay_order_id:
            raise BadRequestException("Order id does not match this booking")

        valid = razorpay_service.verify_payment_signature(
            razorpay_order_id=payload.razorpay_order_id,
            razorpay_payment_id=payload.razorpay_payment_id,
            razorpay_signature=payload.razorpay_signature,
        )
        if not valid:
            booking.payment_status = PaymentStatus.FAILED
            booking.touch()
            await booking.save()
            raise BadRequestException("Payment verification failed")

        booking.payment_status = PaymentStatus.PAID
        booking.razorpay_payment_id = payload.razorpay_payment_id
        booking.amount_paid = booking.total_amount
        booking.touch()
        await booking.save()

        await notification_service.create(
            title="New paid therapy booking",
            message=f"{booking.patient_name} paid Rs.{booking.amount_paid} for {booking.service_category.value.replace('_', ' ')}",
            type=NotificationType.BOOKING,
            reference_id=str(booking.id),
            link="/therapy-bookings",
        )
        if booking.contact_email:
            await email_service.send_booking_confirmation(
                booking.contact_email,
                {
                    "name": booking.patient_name,
                    "service": booking.service_category.value.replace("_", " ").title(),
                    "reference": booking.reference,
                    "date": str(booking.preferred_date),
                },
            )

        return booking

    # ---- Lookup / listing --------------------------------------------------

    async def _get_or_404(self, booking_id: str) -> TherapyBooking:
        booking = await self.repo.get(booking_id)
        if booking is None:
            raise NotFoundException("Therapy booking not found")
        return booking

    async def get_or_404(self, booking_id: str) -> TherapyBooking:
        return await self._get_or_404(booking_id)

    async def paginate(
        self,
        page: int,
        page_size: int,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: int = -1,
        status: Optional[str] = None,
        service_category: Optional[str] = None,
        payment_status: Optional[str] = None,
        patient_id: Optional[str] = None,
        assigned_staff_id: Optional[str] = None,
    ) -> Tuple[List[TherapyBooking], int]:
        filters: Dict[str, Any] = {}
        if status:
            filters["status"] = status
        if service_category:
            filters["service_category"] = service_category
        if payment_status:
            filters["payment_status"] = payment_status
        if patient_id:
            filters["patient_id"] = patient_id
        if assigned_staff_id:
            filters["assigned_staff_id"] = assigned_staff_id
        return await self.repo.paginate(
            filters=filters or None, page=page, page_size=page_size,
            search=search, sort_by=sort_by or "created_at", sort_order=sort_order,
        )

    # ---- Refunds --------------------------------------------------------

    @staticmethod
    def _scheduled_datetime(booking: TherapyBooking) -> dt.datetime:
        start_str = booking.time_slot.split("-")[0].strip()
        hour, minute = (int(p) for p in start_str.split(":")[:2])
        return dt.datetime.combine(booking.preferred_date, dt.time(hour, minute), tzinfo=dt.timezone.utc)

    async def _refund_percent_for_cancellation(self, booking: TherapyBooking, rates: PricingSettings) -> int:
        try:
            scheduled_at = self._scheduled_datetime(booking)
        except (ValueError, IndexError):
            # Unparseable time_slot — fail safe to the full-refund window's spirit.
            return 100
        hours_until_visit = (scheduled_at - dt.datetime.now(dt.timezone.utc)).total_seconds() / 3600
        if hours_until_visit >= rates.cancellation_full_refund_window_hours:
            return 100
        return rates.cancellation_late_refund_percent

    async def _process_refund(self, booking: TherapyBooking, refund_percent: int) -> None:
        if booking.payment_status != PaymentStatus.PAID or not booking.razorpay_payment_id:
            return
        if refund_percent <= 0:
            return
        refund_amount = int(booking.amount_paid * refund_percent / 100 + 0.5)
        if refund_amount <= 0:
            return
        result = await razorpay_service.create_refund(
            payment_id=booking.razorpay_payment_id,
            amount_rupees=refund_amount,
            notes={"booking_id": str(booking.id), "reference": booking.reference},
        )
        booking.refund_amount = refund_amount
        booking.razorpay_refund_id = result.get("id")
        booking.refunded_at = utcnow()
        booking.payment_status = PaymentStatus.REFUNDED
        booking.touch()
        await booking.save()

    async def release_abandoned_slots(self, older_than_minutes: int = 30) -> int:
        """Free slots held by bookings whose payment was never completed.

        A slot is claimed the moment a booking is created so two patients can't
        pay for the same visit. If the patient walks away from the Razorpay
        window that hold would otherwise last forever, silently blocking the
        therapist's calendar. Anything still unpaid after ``older_than_minutes``
        is released and the booking is cancelled.

        Returns the number of bookings released.
        """
        cutoff = utcnow() - dt.timedelta(minutes=older_than_minutes)
        stale = await TherapyBooking.find(
            {
                "payment_status": PaymentStatus.PENDING.value,
                "status": BookingStatus.PENDING.value,
                "slot_id": {"$ne": None},
                "created_at": {"$lt": cutoff},
            }
        ).to_list()

        released = 0
        for booking in stale:
            await self._release_slot(booking)
            booking.slot_id = None
            booking.status = BookingStatus.CANCELLED
            booking.cancellation_reason = "Payment not completed — slot released automatically"
            booking.cancelled_by = "system"
            booking.touch()
            await booking.save()
            released += 1

        return released

    # ---- Workflow -----------------------------------------------------------

    async def _apply_status_transition(
        self, booking: TherapyBooking, status: BookingStatus, admin_notes: Optional[str]
    ) -> TherapyBooking:
        match_filter: Dict[str, Any] = {"_id": booking.id}
        if booking.status not in TERMINAL_STATUSES:
            match_filter["status"] = {"$nin": [s.value for s in TERMINAL_STATUSES]}

        result = await TherapyBooking.get_motor_collection().update_one(
            match_filter,
            {"$set": {"status": status.value, "admin_notes": admin_notes, "updated_at": utcnow()}},
        )
        if result.matched_count == 0:
            raise BadRequestException(
                "This booking was just updated by someone else — please refresh and try again."
            )
        return await self._get_or_404(str(booking.id))

    async def change_status(
        self, booking_id: str, status: BookingStatus, actor: ActorContext, reason: Optional[str] = None
    ) -> TherapyBooking:
        booking = await self._get_or_404(booking_id)

        if booking.status in TERMINAL_STATUSES and status != booking.status:
            raise BadRequestException(f"Booking is already {booking.status} and cannot be changed")
        if status == BookingStatus.APPROVED and booking.payment_status != PaymentStatus.PAID:
            raise BadRequestException("Cannot approve a booking that hasn't been paid for yet")

        admin_notes = booking.admin_notes
        if reason:
            note = f"[{status}] {reason}"
            admin_notes = f"{admin_notes}\n{note}" if admin_notes else note

        was_paid = booking.payment_status == PaymentStatus.PAID
        booking = await self._apply_status_transition(booking, status, admin_notes)

        if status in {BookingStatus.CANCELLED, BookingStatus.REJECTED}:
            await self._release_slot(booking)

        if status == BookingStatus.REJECTED and was_paid:
            # The platform is declining a paid booking (e.g. no therapist available) —
            # this isn't the patient cancelling, so it's always a full refund.
            booking.cancellation_reason = reason
            booking.cancelled_by = "admin"
            await self._process_refund(booking, refund_percent=100)
        elif status == BookingStatus.CANCELLED and was_paid:
            rates = await self.get_rates()
            percent = await self._refund_percent_for_cancellation(booking, rates)
            booking.cancellation_reason = reason
            booking.cancelled_by = "admin"
            booking.touch()
            await booking.save()
            await self._process_refund(booking, refund_percent=percent)

        if booking.status != BookingStatus.PENDING:
            await notification_service.mark_read_by_reference(str(booking.id))

        action_map = {BookingStatus.APPROVED: ActivityAction.APPROVE, BookingStatus.REJECTED: ActivityAction.REJECT}
        await activity_service.log(
            action_map.get(status, ActivityAction.UPDATE), "therapy_bookings",
            user_id=actor.user_id, user_email=actor.email,
            entity_id=str(booking.id), description=f"Therapy booking {status}",
            ip_address=actor.ip_address, user_agent=actor.user_agent,
        )

        # Commission hooks: credit on COMPLETED, reverse on CANCELLED/REJECTED
        if status == BookingStatus.COMPLETED and was_paid and booking.assigned_staff_id:
            try:
                await commission_service.credit_earning(booking)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error("Commission credit failed for %s: %s", booking.reference, exc)
        elif status in {BookingStatus.CANCELLED, BookingStatus.REJECTED}:
            try:
                await commission_service.reverse_earning(str(booking.id))
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error("Commission reversal failed for %s: %s", booking.reference, exc)

        return booking

    async def patient_cancel(self, booking_id: str, patient_id: str, reason: Optional[str]) -> TherapyBooking:
        """Patient-initiated cancellation, subject to the refund-window policy."""
        booking = await self._get_or_404(booking_id)
        if booking.patient_id != patient_id:
            raise ForbiddenException("You don't have access to this booking")
        if booking.status in TERMINAL_STATUSES:
            raise BadRequestException(f"Booking is already {booking.status} and cannot be cancelled")

        was_paid = booking.payment_status == PaymentStatus.PAID
        rates = await self.get_rates()
        percent = await self._refund_percent_for_cancellation(booking, rates) if was_paid else 0

        admin_notes = booking.admin_notes
        note = f"[cancelled by patient] {reason}" if reason else "[cancelled by patient]"
        admin_notes = f"{admin_notes}\n{note}" if admin_notes else note

        booking = await self._apply_status_transition(booking, BookingStatus.CANCELLED, admin_notes)
        booking.cancellation_reason = reason
        booking.cancelled_by = "patient"
        booking.touch()
        await booking.save()

        await self._release_slot(booking)

        if was_paid:
            await self._process_refund(booking, refund_percent=percent)

        await notification_service.mark_read_by_reference(str(booking.id))
        await notification_service.create(
            title="Therapy booking cancelled by patient",
            message=f"{booking.patient_name} cancelled {booking.reference}"
            + (f" — {percent}% refund" if was_paid else ""),
            type=NotificationType.BOOKING,
            reference_id=str(booking.id),
            link="/therapy-bookings",
        )

        # Reverse any commission earned on this booking
        try:
            await commission_service.reverse_earning(str(booking.id))
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Commission reversal failed for patient cancel %s: %s", booking.reference, exc)

        return booking

    async def assign_staff(
        self, booking_id: str, staff_id: str, actor: ActorContext, slot_id: Optional[str] = None
    ) -> TherapyBooking:
        """Assign — or re-assign — a therapist to a booking.

        Re-assignment (e.g. the original therapist falls ill) hands the visit
        to somebody else, so the previous therapist's slot has to be handed
        back or their calendar stays blocked forever. If the admin supplies a
        ``slot_id`` from the new therapist's calendar it is claimed and the
        booking is re-timed to it; otherwise the existing date/time is kept.
        """
        booking = await self._get_or_404(booking_id)
        if booking.status not in ASSIGNABLE_STATUSES:
            raise BadRequestException(
                f"Cannot assign staff to a booking with status '{booking.status}'. The booking must be approved first."
            )

        therapist = await User.get(staff_id)
        if therapist is None or therapist.role != "therapist":
            raise BadRequestException("Selected user is not a therapist")
        if therapist.verification_status != "approved":
            raise BadRequestException("This therapist has not been approved yet")

        allowed_types = ASSIGNABLE_USER_TYPES.get(booking.service_category, set())
        if therapist.user_type not in allowed_types:
            raise BadRequestException(
                f"A {therapist.user_type} cannot be assigned to a {booking.service_category.value} booking"
            )

        if booking.service_category == ServiceCategory.MASSAGE_THERAPY:
            patient_gender = booking.patient_gender.value if booking.patient_gender else None
            if not patient_gender or not therapist.gender or therapist.gender != patient_gender:
                raise BadRequestException(
                    "Massage therapy requires a therapist whose gender matches the patient's (safety policy)"
                )

        previous_staff_id = booking.assigned_staff_id
        previous_staff_name = booking.assigned_staff_name
        is_reassignment = bool(previous_staff_id) and previous_staff_id != staff_id

        # Claim the new therapist's slot first — if it's already taken we must
        # not have released the old one.
        new_slot = None
        if slot_id:
            new_slot = await self._claim_slot(
                slot_id, staff_id, booking.patient_name, booking.patient_id or ""
            )

        if is_reassignment or new_slot is not None:
            await self._release_slot(booking)

        if new_slot is not None:
            booking.slot_id = str(new_slot.id)
            booking.preferred_date = dt.date.fromisoformat(new_slot.date)
            booking.shift = self._shift_for(new_slot.start_time)
            booking.time_slot = f"{new_slot.start_time} - {new_slot.end_time}"
        elif is_reassignment:
            # Handed to a new therapist without a new slot — the old slot is
            # freed above and this booking no longer holds one.
            booking.slot_id = None

        booking.assigned_staff_id = staff_id
        booking.assigned_staff_name = therapist.name
        booking.touch()
        await booking.save()

        if new_slot is not None:
            await TherapistSlot.get_motor_collection().update_one(
                {"_id": new_slot.id},
                {"$set": {"therapy_booking_id": str(booking.id), "booking_reference": booking.reference}},
            )

        await activity_service.log(
            ActivityAction.UPDATE, "therapy_bookings",
            user_id=actor.user_id, user_email=actor.email,
            entity_id=str(booking.id),
            description=(
                f"Reassigned from {previous_staff_name} to {therapist.name}"
                if is_reassignment
                else f"Assigned {therapist.name}"
            ),
            ip_address=actor.ip_address, user_agent=actor.user_agent,
        )
        return booking


therapy_booking_service = TherapyBookingService()
