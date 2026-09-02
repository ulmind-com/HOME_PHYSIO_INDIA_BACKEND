"""Business logic for the priced therapy booking + Razorpay payment flow."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.dependencies.auth import ActorContext
from app.models.base import utcnow
from app.models.enums import ActivityAction, BookingStatus, NotificationType, PaymentStatus, ServiceCategory
from app.models.pricing_settings import PricingSettings
from app.models.therapy_booking import TherapyBooking
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
    async def compute_pricing(payload: TherapyBookingCreate | PricingQuoteRequest) -> pricing_service.PricingResult:
        rates = await TherapyBookingService.get_rates()
        if payload.service_category == ServiceCategory.MASSAGE_THERAPY:
            return pricing_service.price_massage_booking(
                massage_type=payload.massage_type,
                massage_duration_minutes=payload.massage_duration_minutes,
                rates=rates,
            )
        return pricing_service.price_visit_booking(
            service_category=payload.service_category,
            frequency_type=payload.frequency_type,
            daily_visits_per_day=payload.daily_visits_per_day,
            equipment=payload.equipment,
            rates=rates,
        )

    # ---- Create + payment -------------------------------------------------

    async def create_with_payment_order(
        self, payload: TherapyBookingCreate, patient_id: Optional[str]
    ) -> Tuple[TherapyBooking, Dict[str, Any]]:
        pricing = await self.compute_pricing(payload)

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
            preferred_date=payload.preferred_date,
            shift=payload.shift,
            time_slot=payload.time_slot,
            session_duration_minutes=payload.session_duration_minutes,
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
        self, booking_id: str, staff_id: str, actor: ActorContext
    ) -> TherapyBooking:
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

        booking.assigned_staff_id = staff_id
        booking.assigned_staff_name = therapist.name
        booking.touch()
        await booking.save()

        await activity_service.log(
            ActivityAction.UPDATE, "therapy_bookings",
            user_id=actor.user_id, user_email=actor.email,
            entity_id=str(booking.id), description=f"Assigned {therapist.name}",
            ip_address=actor.ip_address, user_agent=actor.user_agent,
        )
        return booking


therapy_booking_service = TherapyBookingService()
