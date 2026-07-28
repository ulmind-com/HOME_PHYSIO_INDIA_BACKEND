"""Activity / audit log document."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pymongo
from pydantic import Field

from app.models.base import TimestampedDocument
from app.models.enums import ActivityAction


class ActivityLog(TimestampedDocument):
    """An audit record of an admin action."""

    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: ActivityAction
    entity: str  # e.g. "booking", "service"
    entity_id: Optional[str] = None
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    class Settings:
        name = "activity_logs"
        indexes = [
            [("user_id", pymongo.ASCENDING)],
            [("action", pymongo.ASCENDING)],
            [("entity", pymongo.ASCENDING)],
            [("created_at", pymongo.DESCENDING)],
        ]
