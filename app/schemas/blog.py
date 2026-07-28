"""Blog schemas: categories and posts."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.base import ImageAsset, SEOMeta
from app.models.enums import ContentStatus
from app.schemas.common import IdTimestampSchema


class BlogCategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    slug: Optional[str] = None
    description: str = ""
    is_active: bool = True
    order: int = 0


class BlogCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    order: Optional[int] = None


class BlogCategoryResponse(IdTimestampSchema):
    name: str
    slug: str
    description: str
    is_active: bool
    order: int


class BlogCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    slug: Optional[str] = None
    excerpt: str = ""
    content: str = ""
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    featured_image: Optional[ImageAsset] = None
    author_name: Optional[str] = None
    seo: SEOMeta = Field(default_factory=SEOMeta)
    is_featured: bool = False
    published_at: Optional[dt.datetime] = None
    status: ContentStatus = ContentStatus.DRAFT


class BlogUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    tags: Optional[List[str]] = None
    featured_image: Optional[ImageAsset] = None
    author_name: Optional[str] = None
    seo: Optional[SEOMeta] = None
    is_featured: Optional[bool] = None
    published_at: Optional[dt.datetime] = None
    status: Optional[ContentStatus] = None


class BlogResponse(IdTimestampSchema):
    title: str
    slug: str
    excerpt: str
    content: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    tags: List[str]
    featured_image: Optional[ImageAsset] = None
    author_name: Optional[str] = None
    seo: SEOMeta
    is_featured: bool
    views: int
    published_at: Optional[dt.datetime] = None
    status: ContentStatus
