"""Therapy equipment catalogue.

Two kinds of equipment live here:

* **platform** — created by admin, offered for every therapist in that
  service category;
* **therapist** — created by a therapist for themselves, offered only when
  a patient books that therapist.

The booking flow calls :func:`list_for_booking`, which merges both.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.helpers import item_response, paginated_response
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, get_current_active_user, require_permission
from app.models.enums import EquipmentOwner, ServiceCategory
from app.models.therapy_equipment import TherapyEquipment
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.therapy_equipment import (
    TherapyEquipmentCreate,
    TherapyEquipmentResponse,
    TherapyEquipmentUpdate,
)
from app.utils.slugify import unique_slug

router = APIRouter(prefix="/therapy-equipment", tags=["Therapy Equipment"])

_equipment: BaseRepository[TherapyEquipment] = BaseRepository(TherapyEquipment)
_equipment.search_fields = ("name", "description")


async def _make_slug(name: str) -> str:
    return await unique_slug(name, lambda s: _equipment.exists({"slug": s}))


def _can_manage(user: User, item: TherapyEquipment) -> bool:
    """Admins manage platform equipment; therapists manage their own."""
    if user.is_superuser:
        return True
    if item.owner_type == EquipmentOwner.THERAPIST:
        return item.therapist_id == str(user.id)
    return False


# ---- Booking flow ------------------------------------------------------


@router.get("/for-booking", summary="Equipment offered for a therapist + category")
async def list_for_booking(
    category: ServiceCategory = Query(..., description="Service category being booked"),
    therapist_id: Optional[str] = Query(None, description="Include this therapist's own equipment"),
    _: User = Depends(get_current_active_user),
) -> dict:
    """Platform equipment for the category, plus that therapist's own items."""
    conditions: List[dict] = [
        {"owner_type": EquipmentOwner.PLATFORM.value, "category": category.value, "is_active": True}
    ]
    if therapist_id:
        conditions.append(
            {
                "owner_type": EquipmentOwner.THERAPIST.value,
                "therapist_id": therapist_id,
                "category": category.value,
                "is_active": True,
            }
        )

    items = await TherapyEquipment.find({"$or": conditions}).sort("+sort_order", "+name").to_list()
    data = [TherapyEquipmentResponse.model_validate(i).model_dump(mode="json") for i in items]
    return success_response(data=data, message="Equipment fetched")


# ---- Therapist self-service -------------------------------------------


@router.get("/mine", summary="List my own equipment (therapist)")
async def list_my_equipment(user: User = Depends(get_current_active_user)) -> dict:
    items = await TherapyEquipment.find(
        {"owner_type": EquipmentOwner.THERAPIST.value, "therapist_id": str(user.id)}
    ).sort("+sort_order", "+name").to_list()
    data = [TherapyEquipmentResponse.model_validate(i).model_dump(mode="json") for i in items]
    return success_response(data=data, message="My equipment fetched")


@router.post("/mine", status_code=201, summary="Add my own equipment (therapist)")
async def create_my_equipment(
    payload: TherapyEquipmentCreate,
    user: User = Depends(get_current_active_user),
) -> dict:
    if user.role != "therapist":
        raise ForbiddenException("Only therapists can add their own equipment")

    item = TherapyEquipment(
        **payload.model_dump(),
        slug=await _make_slug(payload.name),
        owner_type=EquipmentOwner.THERAPIST,
        therapist_id=str(user.id),
        therapist_name=user.name,
    )
    await _equipment.create(item)
    return item_response(TherapyEquipmentResponse, item, "Equipment added")


# ---- Admin catalogue ---------------------------------------------------


@router.get("", summary="List therapy equipment")
async def list_equipment(
    params: PaginationParams = Depends(pagination_params),
    category: Optional[ServiceCategory] = Query(None),
    owner_type: Optional[EquipmentOwner] = Query(None),
    therapist_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    _: ActorContext = Depends(require_permission("therapy_equipment", "view")),
) -> dict:
    filters: dict = {}
    if category:
        filters["category"] = category.value
    if owner_type:
        filters["owner_type"] = owner_type.value
    if therapist_id:
        filters["therapist_id"] = therapist_id
    if is_active is not None:
        filters["is_active"] = is_active

    items, total = await _equipment.paginate(
        page=params.page, page_size=params.page_size, search=params.search,
        sort_by=params.sort_by or "sort_order", sort_order=params.sort_direction,
        filters=filters or None,
    )
    return paginated_response(TherapyEquipmentResponse, items, total, params)


@router.post("", status_code=201, summary="Create platform equipment (admin)")
async def create_equipment(
    payload: TherapyEquipmentCreate,
    _: ActorContext = Depends(require_permission("therapy_equipment", "create")),
) -> dict:
    item = TherapyEquipment(
        **payload.model_dump(),
        slug=await _make_slug(payload.name),
        owner_type=EquipmentOwner.PLATFORM,
    )
    await _equipment.create(item)
    return item_response(TherapyEquipmentResponse, item, "Equipment created")


@router.put("/{equipment_id}", summary="Update equipment")
async def update_equipment(
    equipment_id: str,
    payload: TherapyEquipmentUpdate,
    user: User = Depends(get_current_active_user),
) -> dict:
    item = await _equipment.get(equipment_id)
    if item is None:
        raise NotFoundException("Equipment not found")

    if not _can_manage(user, item):
        # Fall back to the admin permission for platform-owned rows.
        from app.dependencies.auth import _resolve_permissions
        from app.core.permissions import ALL

        perms = await _resolve_permissions(user)
        if ALL not in perms and "therapy_equipment:update" not in perms:
            raise ForbiddenException("You don't have access to this equipment")

    await _equipment.update(item, payload.model_dump(exclude_unset=True))
    return item_response(TherapyEquipmentResponse, item, "Equipment updated")


@router.delete("/{equipment_id}", summary="Delete equipment")
async def delete_equipment(
    equipment_id: str,
    user: User = Depends(get_current_active_user),
) -> dict:
    item = await _equipment.get(equipment_id)
    if item is None:
        raise NotFoundException("Equipment not found")

    if not _can_manage(user, item):
        from app.dependencies.auth import _resolve_permissions
        from app.core.permissions import ALL

        perms = await _resolve_permissions(user)
        if ALL not in perms and "therapy_equipment:delete" not in perms:
            raise ForbiddenException("You don't have access to this equipment")

    await _equipment.delete(item)
    return success_response(message="Equipment deleted")
