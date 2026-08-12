"""Medical equipment, categories and rental endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from app.api.helpers import item_response, paginated_response
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.enums import (
    ContentStatus,
    NotificationType,
    RentalStatus,
)
from app.models.equipment import Equipment, EquipmentCategory, EquipmentRental
from app.repositories.base import BaseRepository
from app.schemas.equipment import (
    EquipmentCategoryCreate,
    EquipmentCategoryResponse,
    EquipmentCategoryUpdate,
    EquipmentCreate,
    EquipmentResponse,
    EquipmentUpdate,
    RentalCreate,
    RentalResponse,
    RentalUpdate,
)
from app.services.crud import CrudService
from app.services.email_service import email_service
from app.services.notification_service import notification_service
from app.utils.references import generate_reference

router = APIRouter(prefix="/equipment", tags=["Medical Equipment"])

_equipment = CrudService(
    Equipment, entity="equipment",
    search_fields=("name", "short_description", "description"),
    slug_source="name",
)
_category = CrudService(
    EquipmentCategory, entity="categories",
    search_fields=("name", "description"), slug_source="name",
)
_rentals: BaseRepository[EquipmentRental] = BaseRepository(EquipmentRental)
_rentals.search_fields = ("reference", "customer_name", "customer_phone")


# ---- Categories -------------------------------------------------------


@router.get("/categories", summary="List equipment categories")
async def list_categories(active_only: bool = Query(True)) -> dict:
    filters = {"is_active": True} if active_only else None
    items = await _category.repo.list(filters=filters, sort=[("order", 1)])
    data = [EquipmentCategoryResponse.model_validate(c).model_dump(mode="json") for c in items]
    return success_response(data=data, message="Categories fetched")


@router.post("/categories", status_code=201, summary="Create equipment category")
async def create_category(
    payload: EquipmentCategoryCreate,
    actor: ActorContext = Depends(require_permission("equipment", "create")),
) -> dict:
    doc = await _category.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(EquipmentCategoryResponse, doc, "Category created")


@router.put("/categories/{category_id}", summary="Update equipment category")
async def update_category(
    category_id: str,
    payload: EquipmentCategoryUpdate,
    actor: ActorContext = Depends(require_permission("equipment", "update")),
) -> dict:
    doc = await _category.update(category_id, payload.model_dump(exclude_unset=True), actor)
    return item_response(EquipmentCategoryResponse, doc, "Category updated")


@router.delete("/categories/{category_id}", summary="Delete equipment category")
async def delete_category(
    category_id: str,
    actor: ActorContext = Depends(require_permission("equipment", "delete")),
) -> dict:
    await _category.delete(category_id, actor)
    return success_response(message="Category deleted")


# ---- Rentals (declared before /{id} to avoid route clashes) -----------


@router.post("/rentals", status_code=201, summary="Submit a rental request (public)")
async def create_rental(
    payload: RentalCreate,
    background_tasks: BackgroundTasks,
) -> dict:
    """Public endpoint: submit an equipment rental request."""
    eq_name = payload.equipment_name or "Unknown Equipment"
    eq_id = payload.equipment_id or ""

    if payload.equipment_id:
        equipment = await _equipment.repo.get(payload.equipment_id)
        if equipment:
            eq_name = equipment.name
            eq_id = str(equipment.id)

    duration_days = None
    if payload.end_date:
        duration_days = max((payload.end_date - payload.start_date).days, 0)

    rental = EquipmentRental(
        reference=generate_reference("NHR"),
        equipment_id=eq_id,
        equipment_name=eq_name,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_email=payload.customer_email,
        address=payload.address,
        start_date=payload.start_date,
        end_date=payload.end_date,
        quantity=payload.quantity,
        duration_days=duration_days,
    )
    await _rentals.create(rental)

    await notification_service.create(
        title="New equipment rental request",
        message=f"{rental.customer_name} requested {rental.equipment_name}",
        type=NotificationType.RENTAL,
        reference_id=str(rental.id),
    )
    if payload.customer_email:
        background_tasks.add_task(
            email_service.send_admin_notification,
            "New Equipment Rental Request",
            f"<p>{rental.customer_name} requested <b>{rental.equipment_name}</b> "
            f"(ref {rental.reference}).</p>",
        )
    return item_response(RentalResponse, rental, "Rental request submitted")


@router.get("/rentals", summary="List rental requests")
async def list_rentals(
    params: PaginationParams = Depends(pagination_params),
    status: Optional[RentalStatus] = Query(None),
    _: ActorContext = Depends(require_permission("rentals", "view")),
) -> dict:
    filters = {"status": status} if status else None
    items, total = await _rentals.paginate(
        filters=filters, page=params.page, page_size=params.page_size,
        search=params.search, sort_by=params.sort_by or "created_at",
        sort_order=params.sort_direction,
    )
    return paginated_response(RentalResponse, items, total, params)


@router.put("/rentals/{rental_id}", summary="Update rental request")
async def update_rental(
    rental_id: str,
    payload: RentalUpdate,
    actor: ActorContext = Depends(require_permission("rentals", "update")),
) -> dict:
    from app.core.exceptions import NotFoundException

    rental = await _rentals.get(rental_id)
    if rental is None:
        raise NotFoundException("Rental not found")
    await _rentals.update(rental, payload.model_dump(exclude_unset=True))
    return item_response(RentalResponse, rental, "Rental updated")


# ---- Equipment CRUD ---------------------------------------------------


@router.get("", summary="List equipment")
async def list_equipment(
    params: PaginationParams = Depends(pagination_params),
    status: Optional[ContentStatus] = Query(None),
    category_id: Optional[str] = Query(None),
    is_available: Optional[bool] = Query(None),
) -> dict:
    filters: dict = {}
    if status:
        filters["status"] = status
    if category_id:
        filters["category_id"] = category_id
    if is_available is not None:
        filters["is_available"] = is_available
    items, total = await _equipment.paginate(
        page=params.page, page_size=params.page_size, search=params.search,
        sort_by=params.sort_by or "order", sort_order=params.sort_direction,
        filters=filters or None,
    )
    return paginated_response(EquipmentResponse, items, total, params)


@router.get("/slug/{slug}", summary="Get equipment by slug")
async def get_equipment_by_slug(slug: str) -> dict:
    doc = await _equipment.get_by_slug(slug)
    return item_response(EquipmentResponse, doc)


@router.get("/{equipment_id}", summary="Get equipment by id")
async def get_equipment(equipment_id: str) -> dict:
    doc = await _equipment.get_or_404(equipment_id)
    return item_response(EquipmentResponse, doc)


@router.post("", status_code=201, summary="Create equipment")
async def create_equipment(
    payload: EquipmentCreate,
    actor: ActorContext = Depends(require_permission("equipment", "create")),
) -> dict:
    doc = await _equipment.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(EquipmentResponse, doc, "Equipment created")


@router.put("/{equipment_id}", summary="Update equipment")
async def update_equipment(
    equipment_id: str,
    payload: EquipmentUpdate,
    actor: ActorContext = Depends(require_permission("equipment", "update")),
) -> dict:
    doc = await _equipment.update(equipment_id, payload.model_dump(exclude_unset=True), actor)
    return item_response(EquipmentResponse, doc, "Equipment updated")


@router.delete("/{equipment_id}", summary="Delete equipment")
async def delete_equipment(
    equipment_id: str,
    actor: ActorContext = Depends(require_permission("equipment", "delete")),
) -> dict:
    await _equipment.delete(equipment_id, actor)
    return success_response(message="Equipment deleted")
