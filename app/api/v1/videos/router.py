"""Video gallery endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.helpers import item_response, paginated_response
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.video import Video
from app.schemas.content import VideoCreate, VideoResponse, VideoUpdate
from app.services.crud import CrudService

router = APIRouter(prefix="/videos", tags=["Videos"])

_video = CrudService(
    Video, entity="videos", search_fields=("title", "description", "category"),
    slug_source="title",
)


@router.get("", summary="List videos")
async def list_videos(
    params: PaginationParams = Depends(pagination_params),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
) -> dict:
    filters: dict = {}
    if category:
        filters["category"] = category
    if is_active is not None:
        filters["is_active"] = is_active
    items, total = await _video.paginate(
        page=params.page, page_size=params.page_size, search=params.search,
        sort_by=params.sort_by or "order", sort_order=params.sort_direction,
        filters=filters or None,
    )
    return paginated_response(VideoResponse, items, total, params)


@router.get("/{video_id}", summary="Get video")
async def get_video(video_id: str) -> dict:
    doc = await _video.get_or_404(video_id)
    return item_response(VideoResponse, doc)


@router.post("", status_code=201, summary="Create video")
async def create_video(
    payload: VideoCreate,
    actor: ActorContext = Depends(require_permission("videos", "create")),
) -> dict:
    doc = await _video.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(VideoResponse, doc, "Video created")


@router.put("/{video_id}", summary="Update video")
async def update_video(
    video_id: str,
    payload: VideoUpdate,
    actor: ActorContext = Depends(require_permission("videos", "update")),
) -> dict:
    doc = await _video.update(video_id, payload.model_dump(exclude_unset=True), actor)
    return item_response(VideoResponse, doc, "Video updated")


@router.delete("/{video_id}", summary="Delete video")
async def delete_video(
    video_id: str,
    actor: ActorContext = Depends(require_permission("videos", "delete")),
) -> dict:
    await _video.delete(video_id, actor)
    return success_response(message="Video deleted")
