"""Booking business logic: creation, workflow transitions and export."""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import BadRequestException, NotFoundException
from app.dependencies.auth import ActorContext
from app.models.booking import Booking
from app.models.enums import ActivityAction, BookingStatus, NotificationType
from app.repositories.base import BaseRepository
from app.services.activity_service import activity_service
from app.services.notification_service import notification_service
from app.utils.references import generate_reference


class BookingService:
    """Coordinates the booking lifecycle."""

    def __init__(self) -> None:
        self.repo: BaseRepository[Booking] = BaseRepository(Booking)
        self.repo.search_fields = (
            "reference",
            "patient_name",
            "contact_phone",
            "service_name",
        )

    async def create(self, data: Dict[str, Any]) -> Booking:
        """Create a booking from a public submission (no auth)."""
        booking = Booking(reference=generate_reference("NHB"), **data)
        await self.repo.create(booking)
        await notification_service.create(
            title="New booking received",
            message=f"{booking.patient_name} booked {booking.service_name}",
            type=NotificationType.BOOKING,
            reference_id=str(booking.id),
        )
        return booking

    async def get_or_404(self, booking_id: str) -> Booking:
        booking = await self.repo.get(booking_id)
        if booking is None:
            raise NotFoundException("Booking not found")
        return booking

    async def update(
        self, booking_id: str, data: Dict[str, Any], actor: ActorContext
    ) -> Booking:
        booking = await self.get_or_404(booking_id)
        await self.repo.update(booking, data)
        await self._audit(ActivityAction.UPDATE, booking, actor, "Updated booking")
        return booking

    async def change_status(
        self,
        booking_id: str,
        status: BookingStatus,
        actor: ActorContext,
        reason: Optional[str] = None,
    ) -> Booking:
        """Transition a booking to a new status with validation."""
        booking = await self.get_or_404(booking_id)

        terminal = {BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.REJECTED}
        if booking.status in terminal and status != booking.status:
            raise BadRequestException(
                f"Booking is already {booking.status} and cannot be changed"
            )

        booking.status = status
        if reason:
            note = f"[{status}] {reason}"
            booking.admin_notes = (
                f"{booking.admin_notes}\n{note}" if booking.admin_notes else note
            )
        booking.touch()
        await booking.save()

        action_map = {
            BookingStatus.APPROVED: ActivityAction.APPROVE,
            BookingStatus.REJECTED: ActivityAction.REJECT,
        }
        await self._audit(
            action_map.get(status, ActivityAction.UPDATE),
            booking, actor, f"Booking {status}",
        )
        return booking

    async def assign_staff(
        self, booking_id: str, staff_id: str, staff_name: str, actor: ActorContext
    ) -> Booking:
        booking = await self.get_or_404(booking_id)
        booking.assigned_staff_id = staff_id
        booking.assigned_staff_name = staff_name
        booking.touch()
        await booking.save()
        await self._audit(
            ActivityAction.UPDATE, booking, actor, f"Assigned {staff_name}"
        )
        return booking

    async def delete(self, booking_id: str, actor: ActorContext) -> None:
        booking = await self.get_or_404(booking_id)
        await self.repo.delete(booking)
        await self._audit(ActivityAction.DELETE, booking, actor, "Deleted booking")

    async def paginate(
        self,
        page: int,
        page_size: int,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: int = -1,
        status: Optional[str] = None,
        service_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Tuple[List[Booking], int]:
        filters: Dict[str, Any] = {}
        if status:
            filters["status"] = status
        if service_id:
            filters["service_id"] = service_id
        if source:
            filters["source"] = source
        date_filter: Dict[str, Any] = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to
        if date_filter:
            filters["preferred_date"] = date_filter
        return await self.repo.paginate(
            filters=filters or None, page=page, page_size=page_size,
            search=search, sort_by=sort_by or "created_at", sort_order=sort_order,
        )

    async def export_csv(self, status: Optional[str] = None, source: Optional[str] = None) -> str:
        """Export bookings as a CSV string."""
        filters = {}
        if status:
            filters["status"] = status
        if source:
            filters["source"] = source
        bookings = await self.repo.list(
            filters=filters, sort=[("created_at", -1)], limit=5000
        )
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["Reference", "Patient", "Phone", "Service", "Preferred Date",
             "Status", "City", "Created At"]
        )
        for b in bookings:
            writer.writerow(
                [b.reference, b.patient_name, b.contact_phone, b.service_name,
                 b.preferred_date, b.status, b.city or "", b.created_at.isoformat()]
            )
        return buffer.getvalue()

    async def _audit(
        self, action: ActivityAction, booking: Booking, actor: ActorContext, desc: str
    ) -> None:
        await activity_service.log(
            action, "bookings", user_id=actor.user_id, user_email=actor.email,
            entity_id=str(booking.id), description=desc,
            ip_address=actor.ip_address, user_agent=actor.user_agent,
        )


booking_service = BookingService()
