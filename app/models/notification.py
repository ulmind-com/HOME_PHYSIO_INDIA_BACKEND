"""Admin notification document."""

from __future__ import annotations

import datetime as dt
from typing import Optional

import pymongo

from app.models.base import TimestampedDocument
from app.models.enums import NotificationType


class Notification(TimestampedDocument):
    """An in-app notification for admin users."""

    # ``None`` user_id means the notification is broadcast to all admins.
    user_id: Optional[str] = None
    type: NotificationType = NotificationType.SYSTEM
    title: str
    message: str = ""
    link: Optional[str] = None
    reference_id: Optional[str] = None
    is_read: bool = False
    read_at: Optional[dt.datetime] = None

    class Settings:
        name = "notifications"
        indexes = [
            [("user_id", pymongo.ASCENDING)],
            [("is_read", pymongo.ASCENDING)],
            [("created_at", pymongo.DESCENDING)],
        ]
