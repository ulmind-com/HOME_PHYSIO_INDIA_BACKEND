"""Services & categories endpoints (public read + admin CRUD)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.helpers import item_response, paginated_response
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.enums import ContentStatus
from app.models.service import Category, Service
from app.schemas.service import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
)
from app.services.crud import CrudService

router = APIRouter(prefix="/services", tags=["Services"])

_service = CrudService(
    Service, entity="services",
    search_fields=("title", "short_description", "description"),
    slug_source="title",
)
_category = CrudService(
    Category, entity="categories", search_fields=("name", "description"),
    slug_source="name",
)


# ---- Categories -------------------------------------------------------


@router.get("/categories", summary="List service categories")
async def list_categories(
    params: PaginationParams = Depends(pagination_params),
    active_only: Optional[bool] = Query(None),
) -> dict:
    """Paginated list of service categories, ordered by ``order``."""
    filters: dict = {}
    if active_only is True:
        filters["is_active"] = True

    items, total = await _category.paginate(
        page=params.page,
        page_size=params.page_size,
        search=params.search,
        sort_by=params.sort_by or "order",
        sort_order=params.sort_direction,
        filters=filters or None,
    )
    return paginated_response(CategoryResponse, items, total, params)


@router.post("/categories", status_code=201, summary="Create service category")
async def create_category(
    payload: CategoryCreate,
    actor: ActorContext = Depends(require_permission("categories", "create")),
) -> dict:
    doc = await _category.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(CategoryResponse, doc, "Category created")


@router.put("/categories/{category_id}", summary="Update service category")
async def update_category(
    category_id: str,
    payload: CategoryUpdate,
    actor: ActorContext = Depends(require_permission("categories", "update")),
) -> dict:
    doc = await _category.update(
        category_id, payload.model_dump(exclude_unset=True), actor
    )
    return item_response(CategoryResponse, doc, "Category updated")


@router.delete("/categories/{category_id}", summary="Delete service category")
async def delete_category(
    category_id: str,
    actor: ActorContext = Depends(require_permission("categories", "delete")),
) -> dict:
    await _category.delete(category_id, actor)
    return success_response(message="Category deleted")


# ---- Services ---------------------------------------------------------


@router.get("", summary="List services")
async def list_services(
    params: PaginationParams = Depends(pagination_params),
    status: Optional[ContentStatus] = Query(None),
    category_id: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
) -> dict:
    """Paginated, filterable, searchable list of services."""
    filters: dict = {}
    if status:
        filters["status"] = status
    if category_id:
        filters["category_id"] = category_id
    if is_featured is not None:
        filters["is_featured"] = is_featured

    items, total = await _service.paginate(
        page=params.page,
        page_size=params.page_size,
        search=params.search,
        sort_by=params.sort_by or "order",
        sort_order=params.sort_direction,
        filters=filters or None,
    )
    return paginated_response(ServiceResponse, items, total, params)


@router.get("/slug/{slug}", summary="Get service by slug")
async def get_service_by_slug(slug: str) -> dict:
    doc = await _service.get_by_slug(slug)
    return item_response(ServiceResponse, doc)


@router.get("/{service_id}", summary="Get service by id")
async def get_service(service_id: str) -> dict:
    doc = await _service.get_or_404(service_id)
    return item_response(ServiceResponse, doc)


@router.post("", status_code=201, summary="Create service")
async def create_service(
    payload: ServiceCreate,
    actor: ActorContext = Depends(require_permission("services", "create")),
) -> dict:
    doc = await _service.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(ServiceResponse, doc, "Service created")


@router.put("/{service_id}", summary="Update service")
async def update_service(
    service_id: str,
    payload: ServiceUpdate,
    actor: ActorContext = Depends(require_permission("services", "update")),
) -> dict:
    doc = await _service.update(
        service_id, payload.model_dump(exclude_unset=True), actor
    )
    return item_response(ServiceResponse, doc, "Service updated")


@router.delete("/{service_id}", summary="Delete service")
async def delete_service(
    service_id: str,
    actor: ActorContext = Depends(require_permission("services", "delete")),
) -> dict:
    await _service.delete(service_id, actor)
    return success_response(message="Service deleted")
