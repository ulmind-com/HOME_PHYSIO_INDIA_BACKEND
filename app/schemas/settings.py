"""Website settings, social links and SEO schemas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.base import ImageAsset
from app.models.settings import ServicesHero, WorkingHour
from app.schemas.common import IdTimestampSchema


# ---- Website settings ----


class WebsiteSettingsUpdate(BaseModel):
    website_name: Optional[str] = None
    tagline: Optional[str] = None
    logo: Optional[ImageAsset] = None
    favicon: Optional[ImageAsset] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None
    google_map_embed: Optional[str] = None
    google_reviews_link: Optional[str] = None
    working_hours: Optional[List[WorkingHour]] = None
    services_hero: Optional[ServicesHero] = None


class WebsiteSettingsResponse(IdTimestampSchema):
    website_name: str
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


# ---- Social links ----


class SocialLinksUpdate(BaseModel):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None
    twitter: Optional[str] = None
    whatsapp: Optional[str] = None


class SocialLinksResponse(IdTimestampSchema):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None
    twitter: Optional[str] = None
    whatsapp: Optional[str] = None


# ---- SEO ----


class SEOSettingsUpsert(BaseModel):
    page_key: str = Field("global", min_length=1, max_length=80)
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    og_image: Optional[str] = None
    schema_markup: Optional[str] = None


class SEOSettingsResponse(IdTimestampSchema):
    page_key: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    og_image: Optional[str] = None
    schema_markup: Optional[str] = None
