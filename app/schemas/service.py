"""Service & category schemas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.base import ImageAsset, SEOMeta
from app.models.enums import ContentStatus
from app.schemas.common import IdTimestampSchema


# ---- Category ----


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    slug: Optional[str] = None
    description: str = ""
    icon: Optional[str] = None
    image: Optional[ImageAsset] = None
    order: int = 0
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    image: Optional[ImageAsset] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(IdTimestampSchema):
    name: str
    slug: str
    description: str
    icon: Optional[str] = None
    image: Optional[ImageAsset] = None
    order: int
    is_active: bool


# ---- Service ----


class ServiceCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    slug: Optional[str] = None
    short_description: str = ""
    description: str = ""
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    icon: Optional[str] = None
    featured_image: Optional[ImageAsset] = None
    gallery: List[ImageAsset] = Field(default_factory=list)
    price: Optional[float] = Field(None, ge=0)
    price_unit: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    seo: SEOMeta = Field(default_factory=SEOMeta)
    is_featured: bool = False
    order: int = 0
    status: ContentStatus = ContentStatus.PUBLISHED


class ServiceUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    slug: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    icon: Optional[str] = None
    featured_image: Optional[ImageAsset] = None
    gallery: Optional[List[ImageAsset]] = None
    price: Optional[float] = Field(None, ge=0)
    price_unit: Optional[str] = None
    features: Optional[List[str]] = None
    seo: Optional[SEOMeta] = None
    is_featured: Optional[bool] = None
    order: Optional[int] = None
    status: Optional[ContentStatus] = None


class ServiceResponse(IdTimestampSchema):
    title: str
    slug: str
    short_description: str
    description: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    icon: Optional[str] = None
    featured_image: Optional[ImageAsset] = None
    gallery: List[ImageAsset] = Field(default_factory=list)
    price: Optional[float] = None
    price_unit: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    seo: SEOMeta = Field(default_factory=SEOMeta)
    is_featured: bool
    order: int
    status: ContentStatus
