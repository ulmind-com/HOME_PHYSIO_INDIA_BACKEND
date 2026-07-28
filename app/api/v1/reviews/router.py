"""Reviews endpoints.

Surfaces the public Google-reviews link (from website settings) together with
an aggregated rating summary computed from published testimonials.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.responses import success_response
from app.models.settings import WebsiteSettings
from app.models.testimonial import Testimonial
from app.repositories.base import BaseRepository

router = APIRouter(prefix="/reviews", tags=["Reviews"])

_testimonials: BaseRepository[Testimonial] = BaseRepository(Testimonial)
_settings: BaseRepository[WebsiteSettings] = BaseRepository(WebsiteSettings)


@router.get("/summary", summary="Aggregated review summary (public)")
async def review_summary() -> dict:
    """Return average rating, rating distribution and the Google reviews link."""
    testimonials = await _testimonials.list(filters={"is_active": True}, limit=5000)
    total = len(testimonials)
    distribution = {str(star): 0 for star in range(1, 6)}
    rating_sum = 0
    for t in testimonials:
        distribution[str(t.rating)] += 1
        rating_sum += t.rating
    average = round(rating_sum / total, 2) if total else 0.0

    website = await _settings.find_one({})
    google_link = website.google_reviews_link if website else None

    return success_response(
        data={
            "total_reviews": total,
            "average_rating": average,
            "distribution": distribution,
            "google_reviews_link": google_link,
        },
        message="Review summary fetched",
    )
