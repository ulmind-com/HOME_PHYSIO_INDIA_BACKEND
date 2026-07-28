"""Notification endpoints for admin users."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.helpers import paginated_response
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, get_actor, require_permission
from app.schemas.misc import NotificationResponse
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", summary="List my notifications")
async def list_notifications(
    params: PaginationParams = Depends(pagination_params),
    is_read: Optional[bool] = Query(None),
    actor: ActorContext = Depends(get_actor),
) -> dict:
    items, total = await notification_service.paginate(
        user_id=actor.user_id, page=params.page, page_size=params.page_size,
        is_read=is_read,
    )
    return paginated_response(NotificationResponse, items, total, params)


@router.get("/unread-count", summary="Unread notification count")
async def unread_count(actor: ActorContext = Depends(get_actor)) -> dict:
    count = await notification_service.unread_count(actor.user_id)
    return success_response(data={"unread": count}, message="Unread count fetched")


@router.post("/{notification_id}/read", summary="Mark notification as read")
async def mark_read(
    notification_id: str,
    actor: ActorContext = Depends(get_actor),
) -> dict:
    notification = await notification_service.mark_read(notification_id, actor.user_id)
    return success_response(
        data=NotificationResponse.model_validate(notification).model_dump(mode="json"),
        message="Notification marked as read",
    )


@router.post("/read-all", summary="Mark all notifications as read")
async def mark_all_read(actor: ActorContext = Depends(get_actor)) -> dict:
    updated = await notification_service.mark_all_read(actor.user_id)
    return success_response(data={"updated": updated}, message="All marked as read")


@router.delete("/{notification_id}", summary="Delete a notification")
async def delete_notification(
    notification_id: str,
    _: ActorContext = Depends(require_permission("notifications", "delete")),
) -> dict:
    await notification_service.delete(notification_id)
    return success_response(message="Notification deleted")
