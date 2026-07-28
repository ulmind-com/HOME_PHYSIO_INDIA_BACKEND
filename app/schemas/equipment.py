"""Medical equipment, category and rental schemas."""

from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.base import ImageAsset, SEOMeta
from app.models.enums import ContentStatus, RentalStatus
from app.schemas.common import IdTimestampSchema


# ---- Equipment category ----


class EquipmentCategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    slug: Optional[str] = None
    description: str = ""
    image: Optional[ImageAsset] = None
    order: int = 0
    is_active: bool = True


class EquipmentCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    image: Optional[ImageAsset] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class EquipmentCategoryResponse(IdTimestampSchema):
    name: str
    slug: str
    description: str
    image: Optional[ImageAsset] = None
    order: int
    is_active: bool


# ---- Equipment ----


class EquipmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    slug: Optional[str] = None
    short_description: str = ""
    description: str = ""
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    featured_image: Optional[ImageAsset] = None
    gallery: List[ImageAsset] = Field(default_factory=list)
    rental_price: Optional[float] = Field(None, ge=0)
    rental_unit: str = "per day"
    security_deposit: Optional[float] = Field(None, ge=0)
    min_rental_duration: Optional[int] = Field(None, ge=0)
    max_rental_duration: Optional[int] = Field(None, ge=0)
    specifications: Dict[str, str] = Field(default_factory=dict)
    stock: int = Field(0, ge=0)
    is_available: bool = True
    seo: SEOMeta = Field(default_factory=SEOMeta)
    is_featured: bool = False
    order: int = 0
    status: ContentStatus = ContentStatus.PUBLISHED


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    featured_image: Optional[ImageAsset] = None
    gallery: Optional[List[ImageAsset]] = None
    rental_price: Optional[float] = Field(None, ge=0)
    rental_unit: Optional[str] = None
    security_deposit: Optional[float] = Field(None, ge=0)
    min_rental_duration: Optional[int] = Field(None, ge=0)
    max_rental_duration: Optional[int] = Field(None, ge=0)
    specifications: Optional[Dict[str, str]] = None
    stock: Optional[int] = Field(None, ge=0)
    is_available: Optional[bool] = None
    seo: Optional[SEOMeta] = None
    is_featured: Optional[bool] = None
    order: Optional[int] = None
    status: Optional[ContentStatus] = None


class EquipmentResponse(IdTimestampSchema):
    name: str
    slug: str
    short_description: str
    description: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    featured_image: Optional[ImageAsset] = None
    gallery: List[ImageAsset] = Field(default_factory=list)
    rental_price: Optional[float] = None
    rental_unit: str
    security_deposit: Optional[float] = None
    min_rental_duration: Optional[int] = None
    max_rental_duration: Optional[int] = None
    specifications: Dict[str, str] = Field(default_factory=dict)
    stock: int
    is_available: bool
    seo: SEOMeta = Field(default_factory=SEOMeta)
    is_featured: bool
    order: int
    status: ContentStatus


# ---- Rental ----


class RentalCreate(BaseModel):
    equipment_id: str
    customer_name: str = Field(..., min_length=2, max_length=120)
    customer_phone: str = Field(..., min_length=6, max_length=20)
    customer_email: Optional[EmailStr] = None
    address: str = Field(..., min_length=3)
    start_date: dt.date
    end_date: Optional[dt.date] = None
    quantity: int = Field(1, ge=1)


class RentalUpdate(BaseModel):
    status: Optional[RentalStatus] = None
    end_date: Optional[dt.date] = None
    quantity: Optional[int] = Field(None, ge=1)
    total_amount: Optional[float] = Field(None, ge=0)
    admin_notes: Optional[str] = None


class RentalResponse(IdTimestampSchema):
    reference: str
    equipment_id: str
    equipment_name: str
    customer_name: str
    customer_phone: str
    customer_email: Optional[EmailStr] = None
    address: str
    start_date: dt.date
    end_date: Optional[dt.date] = None
    quantity: int
    duration_days: Optional[int] = None
    total_amount: Optional[float] = None
    status: RentalStatus
    admin_notes: Optional[str] = None
