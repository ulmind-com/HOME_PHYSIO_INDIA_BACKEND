"""Staff member endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.helpers import item_response, paginated_response
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.staff import StaffMember
from app.schemas.staff import (
    StaffCreate,
    StaffResponse,
    StaffUpdate,
)
from app.services.crud import CrudService

router = APIRouter(prefix="/staff", tags=["Staff"])

_staff = CrudService(
    StaffMember, entity="staff",
    search_fields=("name", "category", "service_label"),
)


@router.get("", summary="List staff members")
async def list_staff(
    params: PaginationParams = Depends(pagination_params),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_featured: Optional[bool] = Query(None),
) -> dict:
    filters: dict = {}
    if category is not None:
        filters["category"] = category
    if is_active is not None:
        filters["is_active"] = is_active
    if is_featured is not None:
        filters["is_featured"] = is_featured
    items, total = await _staff.paginate(
        page=params.page, page_size=params.page_size, search=params.search,
        sort_by=params.sort_by or "order", sort_order=params.sort_direction,
        filters=filters or None,
    )
    return paginated_response(StaffResponse, items, total, params)


@router.get("/{staff_id}", summary="Get staff member")
async def get_staff(staff_id: str) -> dict:
    doc = await _staff.get_or_404(staff_id)
    return item_response(StaffResponse, doc)


@router.post("", status_code=201, summary="Create staff member")
async def create_staff(
    payload: StaffCreate,
    actor: ActorContext = Depends(require_permission("staff", "create")),
) -> dict:
    doc = await _staff.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(StaffResponse, doc, "Staff member created")


@router.put("/{staff_id}", summary="Update staff member")
async def update_staff(
    staff_id: str,
    payload: StaffUpdate,
    actor: ActorContext = Depends(require_permission("staff", "update")),
) -> dict:
    doc = await _staff.update(
        staff_id, payload.model_dump(exclude_unset=True), actor
    )
    return item_response(StaffResponse, doc, "Staff member updated")


@router.delete("/{staff_id}", summary="Delete staff member")
async def delete_staff(
    staff_id: str,
    actor: ActorContext = Depends(require_permission("staff", "delete")),
) -> dict:
    await _staff.delete(staff_id, actor)
    return success_response(message="Staff member deleted")
