"""FAQ endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.helpers import item_response, paginated_response
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.faq import FAQ
from app.schemas.content import FAQCreate, FAQResponse, FAQUpdate
from app.services.crud import CrudService

router = APIRouter(prefix="/faqs", tags=["FAQ"])

_faq = CrudService(FAQ, entity="faqs", search_fields=("question", "answer", "category"))


@router.get("", summary="List FAQs")
async def list_faqs(
    params: PaginationParams = Depends(pagination_params),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
) -> dict:
    filters: dict = {}
    if category:
        filters["category"] = category
    if is_active is not None:
        filters["is_active"] = is_active
    items, total = await _faq.paginate(
        page=params.page, page_size=params.page_size, search=params.search,
        sort_by=params.sort_by or "order", sort_order=params.sort_direction,
        filters=filters or None,
    )
    return paginated_response(FAQResponse, items, total, params)


@router.get("/{faq_id}", summary="Get FAQ")
async def get_faq(faq_id: str) -> dict:
    doc = await _faq.get_or_404(faq_id)
    return item_response(FAQResponse, doc)


@router.post("", status_code=201, summary="Create FAQ")
async def create_faq(
    payload: FAQCreate,
    actor: ActorContext = Depends(require_permission("faqs", "create")),
) -> dict:
    doc = await _faq.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(FAQResponse, doc, "FAQ created")


@router.put("/{faq_id}", summary="Update FAQ")
async def update_faq(
    faq_id: str,
    payload: FAQUpdate,
    actor: ActorContext = Depends(require_permission("faqs", "update")),
) -> dict:
    doc = await _faq.update(faq_id, payload.model_dump(exclude_unset=True), actor)
    return item_response(FAQResponse, doc, "FAQ updated")


@router.delete("/{faq_id}", summary="Delete FAQ")
async def delete_faq(
    faq_id: str,
    actor: ActorContext = Depends(require_permission("faqs", "delete")),
) -> dict:
    await _faq.delete(faq_id, actor)
    return success_response(message="FAQ deleted")
