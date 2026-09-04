"""Therapist directory endpoints for patients."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.helpers import paginated_response
from app.core.pagination import PaginationParams, pagination_params
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserResponse

router = APIRouter(prefix="/therapists", tags=["Therapists"])
_users: BaseRepository[User] = BaseRepository(User)
_users.search_fields = ("name", "specialization")


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
    user: User = Depends(get_current_active_user),  # Must be logged in
) -> dict:
    """Paginated list of admin-approved, active therapists for the directory.

    Massage therapy is gender-matched by policy, so a massage search silently
    restricts results to the caller's own gender — a patient never sees a
    therapist they wouldn't be allowed to book.
    """
    query = {
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

    items, total = await _users.paginate(
        page=params.page,
        page_size=params.page_size,
        search=params.search,
        sort_by=params.sort_by,
        sort_order=params.sort_direction,
        filters=query,
    )
    return paginated_response(UserResponse, items, total, params)
