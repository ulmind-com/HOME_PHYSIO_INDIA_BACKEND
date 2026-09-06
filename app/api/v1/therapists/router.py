"""Therapist directory endpoints for patients."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.helpers import paginated_response
from app.core.exceptions import BadRequestException
from app.core.pagination import PaginationParams, pagination_params
from app.dependencies.auth import get_current_active_user
from app.models.enums import SlotType
from app.models.therapist_slot import TherapistSlot
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import TherapistDirectoryResponse
from app.utils.geo import haversine_km

router = APIRouter(prefix="/therapists", tags=["Therapists"])
_users: BaseRepository[User] = BaseRepository(User)
_users.search_fields = ("name", "specialization")

#: Upper bound on how many matching therapists we'll pull into memory to rank
#: by distance. Ranking happens in Python (Mongo has no geo index on `User`
#: yet), so this keeps worst case bounded. Comfortably above the platform's
#: current therapist count; revisit with a proper `2dsphere` index + $geoNear
#: if the roster ever approaches this.
_LOCATION_RANKING_CAP = 1000


@router.get("", summary="List verified therapists")
async def list_therapists(
    params: PaginationParams = Depends(pagination_params),
    specialization: Optional[str] = Query(None),
    user_type: Optional[str] = Query(
        None, description="physiotherapist | yoga_therapist | massage_therapist"
    ),
    gender: Optional[str] = Query(None, description="Filter to therapists of this gender"),
    match_my_gender: bool = Query(
        False,
        description=(
            "Return only therapists whose gender matches the caller's. Massage "
            "therapy always applies this, whatever the flag says."
        ),
    ),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Searcher's current latitude"),
    lng: Optional[float] = Query(None, ge=-180, le=180, description="Searcher's current longitude"),
    user: User = Depends(get_current_active_user),  # Must be logged in
) -> dict:
    """Paginated list of admin-approved, active therapists for the directory.

    Massage therapy is gender-matched by policy, so a massage search silently
    restricts results to the caller's own gender — a patient never sees a
    therapist they wouldn't be allowed to book.

    When ``lat``/``lng`` are given, results are ranked the way a ride-hailing
    app ranks drivers: therapists with at least one open future home-visit
    slot come first (nearest first within that group), then therapists with
    no open slot right now (nearest first within that group too). Nobody is
    hidden — a fully-booked or location-less therapist still shows up, just
    lower in the list — so the directory stays complete even before every
    therapist has set a location or a slot.
    """
    if (lat is None) != (lng is None):
        raise BadRequestException("lat and lng must be supplied together")

    query: dict = {
        "role": "therapist",
        "is_active": True,
        "verification_status": "approved",
    }
    if specialization:
        query["specialization"] = specialization
    if user_type:
        query["user_type"] = user_type

    wants_massage = user_type == "massage_therapist"
    if gender:
        query["gender"] = gender
    elif wants_massage or match_my_gender:
        if not user.gender:
            # Without a gender on the profile we can't honour the safety rule,
            # so return nothing rather than showing unbookable therapists.
            query["gender"] = "__unset__"
        else:
            query["gender"] = user.gender

    if lat is None:
        # No location given — unchanged behaviour: plain DB-level pagination.
        items, total = await _users.paginate(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_direction,
            filters=query,
        )
        return paginated_response(TherapistDirectoryResponse, items, total, params)

    # Location-ranked path: pull every match (bounded by the safety cap),
    # rank in Python, then paginate the ranked list ourselves.
    candidates, total = await _users.paginate(
        page=1,
        page_size=_LOCATION_RANKING_CAP,
        search=params.search,
        sort_by=params.sort_by,
        sort_order=params.sort_direction,
        filters=query,
    )
    if len(candidates) < total:
        # We hit the ranking cap before exhausting real matches. Report the
        # truncated count instead of the true one so pagination meta never
        # promises a page of results the ranked list can't actually produce.
        total = len(candidates)

    today = dt.date.today().isoformat()
    candidate_ids = [str(c.id) for c in candidates]
    available_ids: set[str] = set()
    if candidate_ids:
        open_slots = await TherapistSlot.find(
            {
                "therapist_id": {"$in": candidate_ids},
                "slot_type": SlotType.HOME_VISIT.value,
                "is_booked": False,
                "date": {"$gte": today},
            }
        ).to_list()
        available_ids = {s.therapist_id for s in open_slots}

    def _distance_km(therapist: User) -> Optional[float]:
        if therapist.lat is None or therapist.lng is None:
            return None
        return haversine_km(lat, lng, therapist.lat, therapist.lng)

    scored = [(c, _distance_km(c)) for c in candidates]
    scored.sort(
        key=lambda pair: (
            str(pair[0].id) not in available_ids,  # False (available) sorts before True
            pair[1] if pair[1] is not None else float("inf"),  # nearest first
        )
    )

    start = (params.page - 1) * params.page_size
    page_slice = scored[start : start + params.page_size]

    results = []
    for therapist, distance in page_slice:
        payload = TherapistDirectoryResponse.model_validate(therapist).model_dump()
        payload["distance_km"] = round(distance, 1) if distance is not None else None
        payload["has_availability"] = str(therapist.id) in available_ids
        results.append(payload)

    return paginated_response(TherapistDirectoryResponse, results, total, params)
