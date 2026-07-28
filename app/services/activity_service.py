"""Activity-log service — records every significant admin action."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.models.activity_log import ActivityLog
from app.models.enums import ActivityAction
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class ActivityService:
    """Create and query audit-log entries."""

    def __init__(self) -> None:
        self.repo: BaseRepository[ActivityLog] = BaseRepository(ActivityLog)
        self.repo.search_fields = ("user_email", "entity", "description")

    async def log(
        self,
        action: ActivityAction,
        entity: str,
        *,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        entity_id: Optional[str] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ActivityLog:
        """Persist an audit-log entry (best-effort — never raises)."""
        entry = ActivityLog(
            action=action,
            entity=entity,
            entity_id=entity_id,
            user_id=user_id,
            user_email=user_email,
            description=description or f"{action} {entity}",
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        try:
            return await self.repo.create(entry)
        except Exception:  # noqa: BLE001 - auditing must never break the request
            logger.exception("Failed to write activity log")
            return entry

    async def paginate(
        self,
        page: int,
        page_size: int,
        search: Optional[str] = None,
        action: Optional[str] = None,
        entity: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Tuple[List[ActivityLog], int]:
        """Paginate audit logs with optional filters."""
        filters: Dict[str, Any] = {}
        if action:
            filters["action"] = action
        if entity:
            filters["entity"] = entity
        if user_id:
            filters["user_id"] = user_id
        return await self.repo.paginate(
            filters=filters, page=page, page_size=page_size, search=search
        )


activity_service = ActivityService()
