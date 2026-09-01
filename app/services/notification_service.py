"""Notification service — in-app admin notifications."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional, Tuple

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.enums import NotificationType
from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationService:
    """Create and manage admin notifications."""

    def __init__(self) -> None:
        self.repo: BaseRepository[Notification] = BaseRepository(Notification)
        self.repo.search_fields = ("title", "message")

    async def create(
        self,
        title: str,
        message: str = "",
        *,
        type: NotificationType = NotificationType.SYSTEM,
        user_id: Optional[str] = None,
        link: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> Notification:
        """Create a notification (broadcast when ``user_id`` is ``None``)."""
        notification = Notification(
            title=title,
            message=message,
            type=type,
            user_id=user_id,
            link=link,
            reference_id=reference_id,
        )
        return await self.repo.create(notification)

    async def paginate(
        self,
        user_id: str,
        page: int,
        page_size: int,
        is_read: Optional[bool] = None,
    ) -> Tuple[List[Notification], int]:
        """List notifications visible to ``user_id`` (own + broadcast)."""
        filters: dict = {"$or": [{"user_id": user_id}, {"user_id": None}]}
        if is_read is not None:
            filters = {"$and": [filters, {"is_read": is_read}]}
        return await self.repo.paginate(
            filters=filters, page=page, page_size=page_size
        )

    async def unread_count(self, user_id: str) -> int:
        """Count unread notifications for ``user_id`` (own + broadcast)."""
        return await self.repo.count(
            {
                "$and": [
                    {"$or": [{"user_id": user_id}, {"user_id": None}]},
                    {"is_read": False},
                ]
            }
        )

    async def mark_read(self, notification_id: str, user_id: str) -> Notification:
        """Mark a single notification as read."""
        notification = await self.repo.get(notification_id)
        if notification is None:
            raise NotFoundException("Notification not found")
        if notification.user_id is not None and notification.user_id != user_id:
            raise ForbiddenException("You don't have access to this notification")
        notification.is_read = True
        notification.read_at = dt.datetime.now(dt.timezone.utc)
        notification.touch()
        await notification.save()
        return notification

    async def mark_all_read(self, user_id: str) -> int:
        """Mark all of a user's notifications as read; returns updated count."""
        now = dt.datetime.now(dt.timezone.utc)
        result = await Notification.find(
            {
                "$and": [
                    {"$or": [{"user_id": user_id}, {"user_id": None}]},
                    {"is_read": False},
                ]
            }
        ).update({"$set": {"is_read": True, "read_at": now, "updated_at": now}})
        return getattr(result, "modified_count", 0)

    async def mark_read_by_reference(self, reference_id: str) -> int:
        """Mark all notifications for a specific entity reference as read."""
        now = dt.datetime.now(dt.timezone.utc)
        result = await Notification.find(
            {"reference_id": reference_id, "is_read": False}
        ).update({"$set": {"is_read": True, "read_at": now, "updated_at": now}})
        return getattr(result, "modified_count", 0)

    async def delete(self, notification_id: str) -> None:
        """Delete a notification."""
        deleted = await self.repo.delete_by_id(notification_id)
        if not deleted:
            raise NotFoundException("Notification not found")


notification_service = NotificationService()
