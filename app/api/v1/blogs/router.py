"""Blog endpoints: categories and posts."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.helpers import item_response, paginated_response
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.blog import Blog, BlogCategory
from app.models.enums import ContentStatus
from app.schemas.blog import (
    BlogCategoryCreate,
    BlogCategoryResponse,
    BlogCategoryUpdate,
    BlogCreate,
    BlogResponse,
    BlogUpdate,
)
from app.services.crud import CrudService

router = APIRouter(prefix="/blogs", tags=["Blogs"])

_blog = CrudService(
    Blog, entity="blogs", search_fields=("title", "excerpt", "content", "tags"),
    slug_source="title",
)
_category = CrudService(
    BlogCategory, entity="categories", search_fields=("name",), slug_source="name",
)


@router.get("/categories", summary="List blog categories")
async def list_categories(active_only: bool = Query(True)) -> dict:
    filters = {"is_active": True} if active_only else None
    items = await _category.repo.list(filters=filters, sort=[("order", 1)])
    data = [BlogCategoryResponse.model_validate(c).model_dump(mode="json") for c in items]
    return success_response(data=data, message="Categories fetched")


@router.post("/categories", status_code=201, summary="Create blog category")
async def create_category(
    payload: BlogCategoryCreate,
    actor: ActorContext = Depends(require_permission("blogs", "create")),
) -> dict:
    doc = await _category.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(BlogCategoryResponse, doc, "Category created")


@router.put("/categories/{category_id}", summary="Update blog category")
async def update_category(
    category_id: str,
    payload: BlogCategoryUpdate,
    actor: ActorContext = Depends(require_permission("blogs", "update")),
) -> dict:
    doc = await _category.update(category_id, payload.model_dump(exclude_unset=True), actor)
    return item_response(BlogCategoryResponse, doc, "Category updated")


@router.delete("/categories/{category_id}", summary="Delete blog category")
async def delete_category(
    category_id: str,
    actor: ActorContext = Depends(require_permission("blogs", "delete")),
) -> dict:
    await _category.delete(category_id, actor)
    return success_response(message="Category deleted")


@router.get("", summary="List blog posts")
async def list_blogs(
    params: PaginationParams = Depends(pagination_params),
    status: Optional[ContentStatus] = Query(None),
    category_id: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
) -> dict:
    filters: dict = {}
    if status:
        filters["status"] = status
    if category_id:
        filters["category_id"] = category_id
    if tag:
        filters["tags"] = tag
    if is_featured is not None:
        filters["is_featured"] = is_featured
    items, total = await _blog.paginate(
        page=params.page, page_size=params.page_size, search=params.search,
        sort_by=params.sort_by or "published_at", sort_order=params.sort_direction,
        filters=filters or None,
    )
    return paginated_response(BlogResponse, items, total, params)


@router.get("/slug/{slug}", summary="Get blog by slug (increments views)")
async def get_blog_by_slug(slug: str) -> dict:
    doc = await _blog.get_by_slug(slug)
    doc.views += 1
    await doc.save()
    return item_response(BlogResponse, doc)


@router.get("/{blog_id}", summary="Get blog by id")
async def get_blog(blog_id: str) -> dict:
    doc = await _blog.get_or_404(blog_id)
    return item_response(BlogResponse, doc)


@router.post("", status_code=201, summary="Create blog post")
async def create_blog(
    payload: BlogCreate,
    actor: ActorContext = Depends(require_permission("blogs", "create")),
) -> dict:
    doc = await _blog.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(BlogResponse, doc, "Blog created")


@router.put("/{blog_id}", summary="Update blog post")
async def update_blog(
    blog_id: str,
    payload: BlogUpdate,
    actor: ActorContext = Depends(require_permission("blogs", "update")),
) -> dict:
    doc = await _blog.update(blog_id, payload.model_dump(exclude_unset=True), actor)
    return item_response(BlogResponse, doc, "Blog updated")


@router.delete("/{blog_id}", summary="Delete blog post")
async def delete_blog(
    blog_id: str,
    actor: ActorContext = Depends(require_permission("blogs", "delete")),
) -> dict:
    await _blog.delete(blog_id, actor)
    return success_response(message="Blog deleted")
