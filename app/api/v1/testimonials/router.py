"""Testimonial endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.helpers import item_response, paginated_response
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.testimonial import Testimonial
from app.schemas.content import (
    TestimonialCreate,
    TestimonialResponse,
    TestimonialUpdate,
)
from app.services.crud import CrudService

router = APIRouter(prefix="/testimonials", tags=["Testimonials"])

_testimonial = CrudService(
    Testimonial, entity="testimonials",
    search_fields=("patient_name", "designation", "message"),
)


@router.get("", summary="List testimonials")
async def list_testimonials(
    params: PaginationParams = Depends(pagination_params),
    is_active: Optional[bool] = Query(None),
    is_featured: Optional[bool] = Query(None),
) -> dict:
    filters: dict = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if is_featured is not None:
        filters["is_featured"] = is_featured
    items, total = await _testimonial.paginate(
        page=params.page, page_size=params.page_size, search=params.search,
        sort_by=params.sort_by or "order", sort_order=params.sort_direction,
        filters=filters or None,
    )
    return paginated_response(TestimonialResponse, items, total, params)


@router.get("/{testimonial_id}", summary="Get testimonial")
async def get_testimonial(testimonial_id: str) -> dict:
    doc = await _testimonial.get_or_404(testimonial_id)
    return item_response(TestimonialResponse, doc)


@router.post("", status_code=201, summary="Create testimonial")
async def create_testimonial(
    payload: TestimonialCreate,
    actor: ActorContext = Depends(require_permission("testimonials", "create")),
) -> dict:
    doc = await _testimonial.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(TestimonialResponse, doc, "Testimonial created")


@router.put("/{testimonial_id}", summary="Update testimonial")
async def update_testimonial(
    testimonial_id: str,
    payload: TestimonialUpdate,
    actor: ActorContext = Depends(require_permission("testimonials", "update")),
) -> dict:
    doc = await _testimonial.update(
        testimonial_id, payload.model_dump(exclude_unset=True), actor
    )
    return item_response(TestimonialResponse, doc, "Testimonial updated")


@router.delete("/{testimonial_id}", summary="Delete testimonial")
async def delete_testimonial(
    testimonial_id: str,
    actor: ActorContext = Depends(require_permission("testimonials", "delete")),
) -> dict:
    await _testimonial.delete(testimonial_id, actor)
    return success_response(message="Testimonial deleted")
