"""Singleton-style website configuration documents.

Each of these collections is expected to hold a single document (the active
configuration). The service layer enforces the singleton semantics.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.base import ImageAsset, TimestampedDocument


class WorkingHour(BaseModel):
    """Opening hours for a single day of the week."""

    day: str
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    is_closed: bool = False


class HeroStat(BaseModel):
    """A single stat displayed in the services hero band (e.g. ``24/7`` → ``Patient Support``)."""

    value: str
    label: str


class HeroSlide(BaseModel):
    """A single slide for the services hero carousel."""

    title: Optional[str] = None
    subtitle: Optional[str] = None
    button_text: Optional[str] = None
    button_link: Optional[str] = None
    background_image: Optional[ImageAsset] = None
    order: int = 0


class ServicesHero(BaseModel):
    """Editable content for the Services page hero section."""

    title: Optional[str] = None
    subtitle: Optional[str] = None
    background_image: Optional[ImageAsset] = None
    stats: List[HeroStat] = Field(default_factory=list)
    slides: List[HeroSlide] = Field(default_factory=list)


class WebsiteSettings(TimestampedDocument):
    """Global website / brand settings."""

    website_name: str = "Nupun Home Health Care Services"
    tagline: Optional[str] = None
    logo: Optional[ImageAsset] = None
    favicon: Optional[ImageAsset] = None

    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None
    google_map_embed: Optional[str] = None
    google_reviews_link: Optional[str] = None

    working_hours: List[WorkingHour] = Field(default_factory=list)

    services_hero: Optional[ServicesHero] = None

    is_active: bool = True

    class Settings:
        name = "website_settings"


class SocialLinks(TimestampedDocument):
    """Social media profile links."""

    facebook: Optional[str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None
    twitter: Optional[str] = None
    whatsapp: Optional[str] = None

    class Settings:
        name = "social_links"


class SEOSettings(TimestampedDocument):
    """Per-page (or global) SEO configuration.

    ``page_key`` identifies the page the settings apply to (e.g. ``home``,
    ``services``, ``global``).
    """

    page_key: str = "global"
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    og_image: Optional[str] = None
    schema_markup: Optional[str] = None

    class Settings:
        name = "seo_settings"
