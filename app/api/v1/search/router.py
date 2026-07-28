"""Global search endpoint spanning multiple collections."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.blog import Blog
from app.models.booking import Booking
from app.models.career import JobApplication
from app.models.equipment import Equipment
from app.models.service import Service

router = APIRouter(prefix="/search", tags=["Search"])


def _regex(term: str) -> dict:
    return {"$regex": term, "$options": "i"}


@router.get("", summary="Global admin search")
async def global_search(
    q: str = Query(..., min_length=1, description="Search term"),
    limit: int = Query(5, ge=1, le=20),
    _: ActorContext = Depends(require_permission("dashboard", "view")),
) -> dict:
    """Search across services, blogs, equipment, bookings and applications."""
    term = q.strip()
    rx = _regex(term)

    services = await Service.find(
        {"$or": [{"title": rx}, {"short_description": rx}]}
    ).limit(limit).to_list()
    blogs = await Blog.find(
        {"$or": [{"title": rx}, {"excerpt": rx}]}
    ).limit(limit).to_list()
    equipment = await Equipment.find(
        {"$or": [{"name": rx}, {"short_description": rx}]}
    ).limit(limit).to_list()
    bookings = await Booking.find(
        {"$or": [{"reference": rx}, {"patient_name": rx}, {"contact_phone": rx}]}
    ).limit(limit).to_list()
    applications = await JobApplication.find(
        {"$or": [{"reference": rx}, {"full_name": rx}, {"email": rx}]}
    ).limit(limit).to_list()

    def brief(items: List, fields: dict) -> List[dict]:
        out = []
        for item in items:
            row = {"id": str(item.id)}
            for out_key, attr in fields.items():
                row[out_key] = getattr(item, attr, None)
            out.append(row)
        return out

    data = {
        "query": term,
        "results": {
            "services": brief(services, {"title": "title", "slug": "slug"}),
            "blogs": brief(blogs, {"title": "title", "slug": "slug"}),
            "equipment": brief(equipment, {"name": "name", "slug": "slug"}),
            "bookings": brief(
                bookings, {"reference": "reference", "patient": "patient_name",
                           "status": "status"}
            ),
            "applications": brief(
                applications, {"reference": "reference", "name": "full_name",
                               "status": "status"}
            ),
        },
    }
    return success_response(data=data, message="Search completed")
