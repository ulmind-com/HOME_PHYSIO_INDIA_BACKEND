"""Priced therapy booking endpoints: pricing quotes, creation, Razorpay
payment, and admin workflow (approve/reject/assign)."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.helpers import item_response, paginated_response
from app.config import settings
from app.core.exceptions import ForbiddenException
from app.core.pagination import PaginationParams, pagination_params
from app.core.permissions import ALL
from app.dependencies.auth import ActorContext, _resolve_permissions, get_current_active_user, require_permission
from app.models.enums import BookingStatus, EquipmentCode, Shift
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


@router.get("/equipment", summary="List portable equipment/modality options")
async def list_equipment(_: User = Depends(get_current_active_user)) -> dict:
    return {"success": True, "data": [e.model_dump() for e in EQUIPMENT_CATALOGUE]}


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


@router.post("/{booking_id}/assign", summary="Assign a therapist to a booking (admin)")
async def assign_staff(
    booking_id: str,
    payload: TherapyBookingAssign,
    actor: ActorContext = Depends(require_permission("therapy_bookings", "update")),
) -> dict:
    booking = await therapy_booking_service.assign_staff(booking_id, payload.assigned_staff_id, actor)
    return item_response(TherapyBookingResponse, booking, "Therapist assigned")
