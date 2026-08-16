"""Service catalogue documents: categories and services."""

from __future__ import annotations

from typing import List, Optional

import pymongo
from beanie import Indexed
from pydantic import Field

from app.models.base import ImageAsset, SEOMeta, TimestampedDocument
from app.models.settings import HeroStat
from app.models.enums import ContentStatus


class Category(TimestampedDocument):
    """A category grouping related services."""

    name: str
    slug: Indexed(str, unique=True)  # type: ignore[valid-type]
    description: str = ""
    icon: Optional[str] = None
    image: Optional[ImageAsset] = None
    
    # Hero Section
    hero_badge: Optional[str] = None
    hero_title: Optional[str] = None
    hero_description: Optional[str] = None
    hero_cta_primary_text: Optional[str] = None
    hero_cta_secondary_text: Optional[str] = None
    hero_image: Optional[ImageAsset] = None # Keeping for backwards compatibility/fallback
    hero_images: List[ImageAsset] = Field(default_factory=list)
    hero_images_mobile: List[ImageAsset] = Field(default_factory=list)
    hero_stats: List[HeroStat] = Field(default_factory=list)

    order: int = 0
    is_active: bool = True

    class Settings:
        name = "categories"
        indexes = [[("slug", pymongo.ASCENDING)], [("order", pymongo.ASCENDING)]]


class Service(TimestampedDocument):
    """A home-health service offered on the platform."""

    title: str
    slug: Indexed(str, unique=True)  # type: ignore[valid-type]
    short_description: str = ""
    description: str = ""
    category_id: Optional[str] = None
    category_name: Optional[str] = None

    icon: Optional[str] = None
    featured_image: Optional[ImageAsset] = None
    gallery: List[ImageAsset] = Field(default_factory=list)

    price: Optional[float] = None
    price_unit: Optional[str] = None  # e.g. "per visit", "per day"
    features: List[str] = Field(default_factory=list)

    seo: SEOMeta = Field(default_factory=SEOMeta)

    is_featured: bool = False
    order: int = 0
    status: ContentStatus = ContentStatus.PUBLISHED

    class Settings:
        name = "services"
        indexes = [
            [("slug", pymongo.ASCENDING)],
            [("category_id", pymongo.ASCENDING)],
            [("status", pymongo.ASCENDING)],
            [("is_featured", pymongo.ASCENDING)],
            [("order", pymongo.ASCENDING)],
            [("title", pymongo.TEXT), ("short_description", pymongo.TEXT)],
        ]
