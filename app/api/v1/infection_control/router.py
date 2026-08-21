"""Infection Control page content and enquiry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.helpers import item_response, paginated_response
from app.core.pagination import PaginationParams
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.infection_control import (
    InfectionControlEnquiry,
    InfectionControlPageContent,
)
from app.repositories.base import BaseRepository
from app.schemas.infection_control import (
    InfectionControlContentResponse,
    InfectionControlContentUpdate,
    InfectionControlEnquiryCreate,
    InfectionControlEnquiryResponse,
    InfectionControlEnquiryStatusUpdate,
)

router = APIRouter(prefix="/infection-control", tags=["Infection Control"])

_content: BaseRepository[InfectionControlPageContent] = BaseRepository(
    InfectionControlPageContent
)
_enquiry: BaseRepository[InfectionControlEnquiry] = BaseRepository(
    InfectionControlEnquiry
)


async def _get_or_create_content() -> InfectionControlPageContent:
    doc = await _content.find_one({})
    if doc is None:
        doc = InfectionControlPageContent()
        await _content.create(doc)
    return doc


# ── Page content (singleton) ─────────────────────────────────────


@router.get("", summary="Get Infection Control page content (public)")
async def get_content() -> dict:
    doc = await _get_or_create_content()
    return item_response(InfectionControlContentResponse, doc)


@router.put("", summary="Update Infection Control page content")
async def update_content(
    payload: InfectionControlContentUpdate,
    actor: ActorContext = Depends(require_permission("settings", "update")),
) -> dict:
    doc = await _get_or_create_content()
    await _content.update(doc, payload.model_dump(exclude_unset=True))
    return item_response(
        InfectionControlContentResponse, doc, "Infection Control page updated"
    )


# ── Enquiries ────────────────────────────────────────────────────


@router.post("/enquiry", summary="Submit an Infection Control enquiry (public)")
async def create_enquiry(payload: InfectionControlEnquiryCreate) -> dict:
    doc = InfectionControlEnquiry(**payload.model_dump())
    await _enquiry.create(doc)
    return item_response(
        InfectionControlEnquiryResponse, doc, "Enquiry submitted successfully"
    )


@router.get("/enquiries", summary="List Infection Control enquiries")
async def list_enquiries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    _: ActorContext = Depends(require_permission("bookings", "view")),
) -> dict:
    filters = {}
    if status:
        filters["status"] = status
    params = PaginationParams(page=page, page_size=page_size)
    items, total = await _enquiry.paginate(filters=filters, params=params)
    return paginated_response(
        InfectionControlEnquiryResponse, items, total, params, "Enquiries fetched"
    )


@router.patch("/enquiries/{enquiry_id}", summary="Update enquiry status")
async def update_enquiry_status(
    enquiry_id: str,
    payload: InfectionControlEnquiryStatusUpdate,
    _: ActorContext = Depends(require_permission("bookings", "update")),
) -> dict:
    doc = await _enquiry.get(enquiry_id)
    if doc is None:
        from app.core.exceptions import NotFoundException

        raise NotFoundException("Enquiry not found")
    await _enquiry.update(doc, {"status": payload.status})
    return item_response(
        InfectionControlEnquiryResponse, doc, "Enquiry status updated"
    )
