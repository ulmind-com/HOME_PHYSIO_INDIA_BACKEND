"""Therapy equipment schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.models.base import ImageAsset
from app.models.enums import EquipmentOwner, ServiceCategory
from app.schemas.common import IdTimestampSchema


class TherapyEquipmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: str = Field("", max_length=600)
    category: ServiceCategory
    charge: int = Field(..., ge=0, le=100000)
    image: Optional[ImageAsset] = None
    is_active: bool = True
    sort_order: int = 0


class TherapyEquipmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=600)
    category: Optional[ServiceCategory] = None
    charge: Optional[int] = Field(None, ge=0, le=100000)
    image: Optional[ImageAsset] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class TherapyEquipmentResponse(IdTimestampSchema):
    name: str
    slug: str
    description: str
    category: ServiceCategory
    charge: int
    owner_type: EquipmentOwner
    therapist_id: Optional[str] = None
    therapist_name: Optional[str] = None
    image: Optional[ImageAsset] = None
    is_active: bool
    sort_order: int
