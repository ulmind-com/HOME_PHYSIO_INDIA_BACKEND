"""Dashboard & analytics endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.helpers import paginated_response, serialize_list
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.schemas.booking import BookingResponse
from app.schemas.career import ApplicationResponse
from app.schemas.content import ContactResponse
from app.schemas.misc import ActivityLogResponse
from app.services.activity_service import activity_service
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", summary="Dashboard stat cards")
async def stats(
    _: ActorContext = Depends(require_permission("dashboard", "view")),
) -> dict:
    return success_response(data=await dashboard_service.stats(), message="Stats fetched")


@router.get("/charts", summary="Charts data (status breakdown + trend)")
async def charts(
    days: int = Query(30, ge=1, le=365),
    _: ActorContext = Depends(require_permission("dashboard", "view")),
) -> dict:
    return success_response(
        data={
            "booking_status": await dashboard_service.booking_status_breakdown(),
            "bookings_trend": await dashboard_service.bookings_trend(days),
        },
        message="Charts data fetched",
    )


@router.get("/recent-bookings", summary="Recent bookings")
async def recent_bookings(
    limit: int = Query(5, ge=1, le=50),
    _: ActorContext = Depends(require_permission("dashboard", "view")),
) -> dict:
    items = await dashboard_service.recent_bookings(limit)
    return success_response(
        data=serialize_list(BookingResponse, items), message="Recent bookings fetched"
    )


@router.get("/recent-contacts", summary="Recent contact messages")
async def recent_contacts(
    limit: int = Query(5, ge=1, le=50),
    _: ActorContext = Depends(require_permission("dashboard", "view")),
) -> dict:
    items = await dashboard_service.recent_contacts(limit)
    return success_response(
        data=serialize_list(ContactResponse, items), message="Recent contacts fetched"
    )


@router.get("/recent-applications", summary="Recent job applications")
async def recent_applications(
    limit: int = Query(5, ge=1, le=50),
    _: ActorContext = Depends(require_permission("dashboard", "view")),
) -> dict:
    items = await dashboard_service.recent_applications(limit)
    return success_response(
        data=serialize_list(ApplicationResponse, items),
        message="Recent applications fetched",
    )


@router.get("/activity-logs", summary="List admin activity / audit logs")
async def activity_logs(
    params: PaginationParams = Depends(pagination_params),
    action: Optional[str] = Query(None),
    entity: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    _: ActorContext = Depends(require_permission("activity_logs", "view")),
) -> dict:
    items, total = await activity_service.paginate(
        page=params.page, page_size=params.page_size, search=params.search,
        action=action, entity=entity, user_id=user_id,
    )
    return paginated_response(ActivityLogResponse, items, total, params)
