"""Booking endpoints: public create + admin workflow, filters and export."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api.helpers import item_response, paginated_response
from app.config import settings
from app.core.limiter import limiter
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.enums import BookingStatus
from app.schemas.booking import (
    BookingAssign,
    BookingCreate,
    BookingResponse,
    BookingStatusUpdate,
    BookingUpdate,
)
from app.services.booking_service import booking_service
from app.services.email_service import email_service

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", status_code=201, summary="Create booking (public)")
async def create_booking(
    request: Request,
    payload: BookingCreate,
    background_tasks: BackgroundTasks,
) -> dict:
    """Public endpoint: submit a service booking from the website."""
    booking = await booking_service.create(payload.model_dump(exclude_unset=True))
    if booking.contact_email:
        background_tasks.add_task(
            email_service.send_booking_confirmation,
            booking.contact_email,
            {
                "name": booking.patient_name,
                "service": booking.service_name,
                "reference": booking.reference,
                "date": str(booking.preferred_date),
            },
        )
    return item_response(BookingResponse, booking, "Booking submitted successfully")


@router.get("", summary="List bookings")
async def list_bookings(
    params: PaginationParams = Depends(pagination_params),
    status: Optional[BookingStatus] = Query(None),
    service_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="ISO date lower bound"),
    date_to: Optional[str] = Query(None, description="ISO date upper bound"),
    source: Optional[str] = Query(None, description="Filter by source"),
    _: ActorContext = Depends(require_permission("bookings", "view")),
) -> dict:
    items, total = await booking_service.paginate(
        page=params.page, page_size=params.page_size, search=params.search,
        sort_by=params.sort_by, sort_order=params.sort_direction,
        status=status, service_id=service_id, date_from=date_from, date_to=date_to,
        source=source,
    )
    return paginated_response(BookingResponse, items, total, params)


@router.get("/export", summary="Export bookings as CSV")
async def export_bookings(
    status: Optional[BookingStatus] = Query(None),
    source: Optional[str] = Query(None),
    _: ActorContext = Depends(require_permission("bookings", "view")),
) -> StreamingResponse:
    csv_data = await booking_service.export_csv(status=status, source=source)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bookings.csv"},
    )


@router.get("/{booking_id}", summary="Get booking")
async def get_booking(
    booking_id: str,
    _: ActorContext = Depends(require_permission("bookings", "view")),
) -> dict:
    booking = await booking_service.get_or_404(booking_id)
    return item_response(BookingResponse, booking)


@router.put("/{booking_id}", summary="Update booking")
async def update_booking(
    booking_id: str,
    payload: BookingUpdate,
    actor: ActorContext = Depends(require_permission("bookings", "update")),
) -> dict:
    booking = await booking_service.update(
        booking_id, payload.model_dump(exclude_unset=True), actor
    )
    return item_response(BookingResponse, booking, "Booking updated")


@router.post("/{booking_id}/approve", summary="Approve booking")
async def approve_booking(
    booking_id: str,
    actor: ActorContext = Depends(require_permission("bookings", "update")),
) -> dict:
    booking = await booking_service.change_status(
        booking_id, BookingStatus.APPROVED, actor
    )
    return item_response(BookingResponse, booking, "Booking approved")


@router.post("/{booking_id}/reject", summary="Reject booking")
async def reject_booking(
    booking_id: str,
    payload: BookingStatusUpdate,
    actor: ActorContext = Depends(require_permission("bookings", "update")),
) -> dict:
    booking = await booking_service.change_status(
        booking_id, BookingStatus.REJECTED, actor, reason=payload.reason
    )
    return item_response(BookingResponse, booking, "Booking rejected")


@router.post("/{booking_id}/cancel", summary="Cancel booking")
async def cancel_booking(
    booking_id: str,
    payload: BookingStatusUpdate,
    actor: ActorContext = Depends(require_permission("bookings", "update")),
) -> dict:
    booking = await booking_service.change_status(
        booking_id, BookingStatus.CANCELLED, actor, reason=payload.reason
    )
    return item_response(BookingResponse, booking, "Booking cancelled")


@router.post("/{booking_id}/assign", summary="Assign staff to booking")
async def assign_booking(
    booking_id: str,
    payload: BookingAssign,
    actor: ActorContext = Depends(require_permission("bookings", "update")),
) -> dict:
    booking = await booking_service.assign_staff(
        booking_id, payload.assigned_staff_id, payload.assigned_staff_name, actor
    )
    return item_response(BookingResponse, booking, "Staff assigned")


@router.delete("/{booking_id}", summary="Delete booking")
async def delete_booking(
    booking_id: str,
    actor: ActorContext = Depends(require_permission("bookings", "delete")),
) -> dict:
    await booking_service.delete(booking_id, actor)
    return success_response(message="Booking deleted")
