"""Schemas for notifications, activity logs and uploads."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from pydantic import BaseModel

from app.models.enums import ActivityAction, NotificationType
from app.schemas.common import IdTimestampSchema


class NotificationResponse(IdTimestampSchema):
    user_id: Optional[str] = None
    type: NotificationType
    title: str
    message: str
    link: Optional[str] = None
    reference_id: Optional[str] = None
    is_read: bool
    read_at: Optional[dt.datetime] = None


class ActivityLogResponse(IdTimestampSchema):
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: ActivityAction
    entity: str
    entity_id: Optional[str] = None
    description: str
    metadata: Dict[str, Any] = {}
    ip_address: Optional[str] = None


class UploadResponse(BaseModel):
    url: str
    public_id: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    resource_type: Optional[str] = None
    bytes: Optional[int] = None
