"""Priced therapy booking endpoints: pricing quotes, creation, Razorpay
payment, and admin workflow (approve/reject/assign)."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.api.helpers import item_response, paginated_response
from app.config import settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.pagination import PaginationParams, pagination_params
from app.core.permissions import ALL
from app.dependencies.auth import ActorContext, _resolve_permissions, get_current_active_user, require_permission
from app.models.enums import BookingStatus, EquipmentCode, Shift, SlotType
from app.models.therapist_slot import TherapistSlot
from app.models.user import User
from app.schemas.therapy_booking import (
    PaymentVerifyRequest,
    PricingQuoteRequest,
    PricingQuoteResponse,
    TherapyBookingAssign,
    TherapyBookingCreate,
    TherapyBookingPaymentInit,
    TherapyBookingResponse,
    TherapyBookingStatusUpdate,
)
from app.services.therapy_booking_service import therapy_booking_service

router = APIRouter(prefix="/therapy-bookings", tags=["Therapy Bookings"])


class HomeVisitSlotCreate(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")


class EquipmentOption(BaseModel):
    code: str
    name: str
    charge: int


EQUIPMENT_CATALOGUE: List[EquipmentOption] = [
    EquipmentOption(code=EquipmentCode.IFT.value, name="IFT (Interferential Therapy)", charge=100),
    EquipmentOption(code=EquipmentCode.TENS.value, name="TENS", charge=100),
    EquipmentOption(code=EquipmentCode.UST.value, name="Ultrasound Therapy (UST)", charge=100),
    EquipmentOption(code=EquipmentCode.NMES.value, name="NMES", charge=100),
    EquipmentOption(code=EquipmentCode.FES.value, name="FES", charge=100),
    EquipmentOption(code=EquipmentCode.PORTABLE_EMS.value, name="Portable EMS", charge=100),
    EquipmentOption(code=EquipmentCode.WAX_BATH.value, name="Wax Bath Therapy", charge=100),
    EquipmentOption(code=EquipmentCode.HOT_COLD.value, name="Hot/Cold Therapy", charge=100),
    EquipmentOption(code=EquipmentCode.THERABAND.value, name="TheraBand / Resistance Band", charge=100),
]

# Static representative slots per shift. There is no per-therapist calendar
# yet, so these are illustrative options rather than live availability.
TIME_SLOTS = {
    Shift.MORNING: ["07:00 - 07:40", "08:00 - 08:40", "09:00 - 09:40", "10:00 - 10:40"],
    Shift.NOON: ["12:00 - 12:40", "13:00 - 13:40"],
    Shift.AFTERNOON: ["15:00 - 15:40", "16:00 - 16:40", "17:00 - 17:40"],
    Shift.EVENING: ["18:00 - 18:40", "19:00 - 19:40", "20:00 - 20:40"],
}


@router.get("/equipment", summary="List portable equipment/modality options (legacy)")
async def list_equipment(_: User = Depends(get_current_active_user)) -> dict:
    """Superseded by ``GET /therapy-equipment/for-booking``, which is
    category-aware and includes the therapist's own equipment. Kept so older
    clients keep working."""
    return {"success": True, "data": [e.model_dump() for e in EQUIPMENT_CATALOGUE]}


@router.get("/therapist-availability", summary="Free home-visit slots for a therapist")
async def therapist_availability(
    therapist_id: str = Query(...),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to today"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    include_booked: bool = Query(False, description="Also return already-taken slots (greyed out in UI)"),
    _: User = Depends(get_current_active_user),
) -> dict:
    """What the patient picks from — only this therapist's home-visit slots.

    Past dates are never returned, and taken slots are excluded unless the
    caller explicitly asks for them so the UI can grey them out.
    """
    start = date_from or dt.date.today().isoformat()
    query: dict = {
        "therapist_id": therapist_id,
        "slot_type": SlotType.HOME_VISIT.value,
        "date": {"$gte": start},
    }
    if date_to:
        query["date"]["$lte"] = date_to
    if not include_booked:
        query["is_booked"] = False

    slots = await TherapistSlot.find(query).sort("+date", "+start_time").to_list()
    data = [
        {
            "id": str(s.id),
            "date": s.date,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "is_booked": s.is_booked,
        }
        for s in slots
    ]
    return {"success": True, "data": data}


@router.get("/my-slots", summary="My published home-visit slots (therapist)")
async def my_slots(
    date_from: Optional[str] = Query(None),
    user: User = Depends(get_current_active_user),
) -> dict:
    query: dict = {"therapist_id": str(user.id), "slot_type": SlotType.HOME_VISIT.value}
    if date_from:
        query["date"] = {"$gte": date_from}
    slots = await TherapistSlot.find(query).sort("+date", "+start_time").to_list()
    data = [
        {
            "id": str(s.id),
            "date": s.date,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "is_booked": s.is_booked,
            "booked_by_patient_name": s.booked_by_patient_name,
            "booking_reference": s.booking_reference,
        }
        for s in slots
    ]
    return {"success": True, "data": data}


@router.post("/my-slots", status_code=201, summary="Publish a home-visit slot (therapist)")
async def create_my_slot(
    payload: HomeVisitSlotCreate,
    user: User = Depends(get_current_active_user),
) -> dict:
    if user.role != "therapist":
        raise ForbiddenException("Only therapists can publish slots")
    if user.verification_status != "approved":
        raise ForbiddenException("Your account is still pending approval")

    existing = await TherapistSlot.find_one(
        {
            "therapist_id": str(user.id),
            "slot_type": SlotType.HOME_VISIT.value,
            "date": payload.date,
            "start_time": payload.start_time,
        }
    )
    if existing:
        raise BadRequestException("You already have a slot starting at that time on that date")

    slot = TherapistSlot(
        therapist_id=str(user.id),
        therapist_name=user.name,
        slot_type=SlotType.HOME_VISIT,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await slot.insert()
    return {"success": True, "message": "Slot published", "data": {"id": str(slot.id)}}


@router.delete("/my-slots/{slot_id}", summary="Remove one of my slots (therapist)")
async def delete_my_slot(slot_id: str, user: User = Depends(get_current_active_user)) -> dict:
    slot = await TherapistSlot.get(slot_id)
    if slot is None:
        raise NotFoundException("Slot not found")
    if slot.therapist_id != str(user.id) and not user.is_superuser:
        raise ForbiddenException("That slot isn't yours")
    if slot.is_booked:
        raise BadRequestException("This slot is already booked — cancel the booking first")
    await slot.delete()
    return {"success": True, "message": "Slot removed"}


@router.get("/time-slots", summary="List available time slots for a shift")
async def list_time_slots(shift: Shift = Query(...), _: User = Depends(get_current_active_user)) -> dict:
    return {"success": True, "data": TIME_SLOTS[shift]}


@router.post("/quote", summary="Get a live price quote for a draft selection")
async def get_quote(payload: PricingQuoteRequest, _: User = Depends(get_current_active_user)) -> dict:
    pricing = await therapy_booking_service.compute_pricing(payload)
    data = PricingQuoteResponse(
        visit_fee=pricing.visit_fee,
        machine_charge=pricing.machine_charge,
        total_amount=pricing.total_amount,
        platform_fee_percent=pricing.platform_fee_percent,
        platform_fee_amount=pricing.platform_fee_amount,
        therapist_payout=pricing.therapist_payout,
    )
    return {"success": True, "data": data.model_dump()}


@router.post("", status_code=201, summary="Create a therapy booking and Razorpay order")
async def create_booking(
    payload: TherapyBookingCreate,
    user: User = Depends(get_current_active_user),
) -> dict:
    booking, order = await therapy_booking_service.create_with_payment_order(payload, patient_id=str(user.id))
    data = TherapyBookingPaymentInit(
        booking=TherapyBookingResponse.model_validate(booking),
        razorpay_order_id=order["id"],
        razorpay_key_id=settings.RAZORPAY_KEY_ID,
        amount=booking.total_amount * 100,
    )
    return {"success": True, "message": "Booking created — complete payment to confirm", "data": data.model_dump(mode="json")}


@router.post("/{booking_id}/verify-payment", summary="Verify a Razorpay payment and confirm the booking")
async def verify_payment(
    booking_id: str,
    payload: PaymentVerifyRequest,
    user: User = Depends(get_current_active_user),
) -> dict:
    booking = await therapy_booking_service.get_or_404(booking_id)
    if booking.patient_id != str(user.id):
        raise ForbiddenException("You don't have access to this booking")
    booking = await therapy_booking_service.verify_payment(booking_id, payload)
    return item_response(TherapyBookingResponse, booking, "Payment verified — booking confirmed")


@router.post("/{booking_id}/cancel", summary="Cancel my therapy booking (patient)")
async def cancel_my_booking(
    booking_id: str,
    payload: TherapyBookingStatusUpdate,
    user: User = Depends(get_current_active_user),
) -> dict:
    booking = await therapy_booking_service.patient_cancel(booking_id, str(user.id), payload.reason)
    return item_response(TherapyBookingResponse, booking, "Booking cancelled")


@router.get("/me", summary="List my therapy bookings")
async def list_my_bookings(
    params: PaginationParams = Depends(pagination_params),
    user: User = Depends(get_current_active_user),
) -> dict:
    items, total = await therapy_booking_service.paginate(
        page=params.page, page_size=params.page_size, patient_id=str(user.id),
    )
    return paginated_response(TherapyBookingResponse, items, total, params)


@router.get("/assigned-to-me", summary="List therapy bookings assigned to me")
async def list_assigned_to_me(
    params: PaginationParams = Depends(pagination_params),
    user: User = Depends(get_current_active_user),
) -> dict:
    items, total = await therapy_booking_service.paginate(
        page=params.page, page_size=params.page_size, assigned_staff_id=str(user.id),
    )
    return paginated_response(TherapyBookingResponse, items, total, params)


@router.get("", summary="List therapy bookings (admin)")
async def list_bookings(
    params: PaginationParams = Depends(pagination_params),
    status: Optional[BookingStatus] = Query(None),
    service_category: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    _: ActorContext = Depends(require_permission("therapy_bookings", "view")),
) -> dict:
    items, total = await therapy_booking_service.paginate(
        page=params.page, page_size=params.page_size, search=params.search,
        sort_by=params.sort_by, sort_order=params.sort_direction,
        status=status, service_category=service_category, payment_status=payment_status,
    )
    return paginated_response(TherapyBookingResponse, items, total, params)


@router.get("/{booking_id}", summary="Get a therapy booking")
async def get_booking(booking_id: str, user: User = Depends(get_current_active_user)) -> dict:
    booking = await therapy_booking_service.get_or_404(booking_id)
    is_owner = booking.patient_id == str(user.id)
    is_assigned = booking.assigned_staff_id == str(user.id)
    if not is_owner and not is_assigned:
        perms = await _resolve_permissions(user)
        if ALL not in perms and "therapy_bookings:view" not in perms:
            raise ForbiddenException("You don't have access to this booking")
    return item_response(TherapyBookingResponse, booking)


@router.patch("/{booking_id}/status", summary="Change a therapy booking's status (admin)")
async def update_status(
    booking_id: str,
    status: BookingStatus,
    payload: TherapyBookingStatusUpdate,
    actor: ActorContext = Depends(require_permission("therapy_bookings", "update")),
) -> dict:
    booking = await therapy_booking_service.change_status(booking_id, status, actor, reason=payload.reason)
    return item_response(TherapyBookingResponse, booking, f"Booking {status}")


@router.patch("/{booking_id}/my-status", summary="Update a booking assigned to me (therapist)")
async def therapist_update_status(
    booking_id: str,
    status: BookingStatus,
    payload: TherapyBookingStatusUpdate,
    request: Request,
    user: User = Depends(get_current_active_user),
) -> dict:
    """Let the assigned therapist move their own booking along.

    Deliberately narrower than the admin endpoint: a therapist can confirm a
    visit, start it, finish it, or cancel it — but can't approve an unpaid
    booking or touch someone else's work.
    """
    booking = await therapy_booking_service.get_or_404(booking_id)
    if booking.assigned_staff_id != str(user.id):
        raise ForbiddenException("This booking isn't assigned to you")

    allowed = {
        BookingStatus.APPROVED,
        BookingStatus.IN_PROGRESS,
        BookingStatus.COMPLETED,
        BookingStatus.CANCELLED,
    }
    if status not in allowed:
        raise BadRequestException(f"Therapists can't set a booking to '{status}'")

    actor = ActorContext(
        user=user,
        ip_address=request.headers.get("X-Forwarded-For") or (request.client.host if request.client else None),
        user_agent=request.headers.get("User-Agent"),
    )
    booking = await therapy_booking_service.change_status(booking_id, status, actor, reason=payload.reason)
    return item_response(TherapyBookingResponse, booking, f"Booking {status}")


@router.post("/{booking_id}/assign", summary="Assign a therapist to a booking (admin)")
async def assign_staff(
    booking_id: str,
    payload: TherapyBookingAssign,
    actor: ActorContext = Depends(require_permission("therapy_bookings", "update")),
) -> dict:
    booking = await therapy_booking_service.assign_staff(booking_id, payload.assigned_staff_id, actor)
    return item_response(TherapyBookingResponse, booking, "Therapist assigned")
