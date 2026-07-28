"""Blog documents: categories and posts."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

import pymongo
from beanie import Indexed
from pydantic import Field

from app.models.base import ImageAsset, SEOMeta, TimestampedDocument
from app.models.enums import ContentStatus


class BlogCategory(TimestampedDocument):
    """A category grouping blog posts."""

    name: str
    slug: Indexed(str, unique=True)  # type: ignore[valid-type]
    description: str = ""
    is_active: bool = True
    order: int = 0

    class Settings:
        name = "blog_categories"
        indexes = [[("slug", pymongo.ASCENDING)]]


class Blog(TimestampedDocument):
    """A blog post / article."""

    title: str
    slug: Indexed(str, unique=True)  # type: ignore[valid-type]
    excerpt: str = ""
    content: str = ""

    category_id: Optional[str] = None
    category_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    featured_image: Optional[ImageAsset] = None
    author_name: Optional[str] = None

    seo: SEOMeta = Field(default_factory=SEOMeta)

    is_featured: bool = False
    views: int = 0
    published_at: Optional[dt.datetime] = None
    status: ContentStatus = ContentStatus.DRAFT

    class Settings:
        name = "blogs"
        indexes = [
            [("slug", pymongo.ASCENDING)],
            [("category_id", pymongo.ASCENDING)],
            [("status", pymongo.ASCENDING)],
            [("is_featured", pymongo.ASCENDING)],
            [("published_at", pymongo.DESCENDING)],
            [("title", pymongo.TEXT), ("excerpt", pymongo.TEXT), ("content", pymongo.TEXT)],
        ]
