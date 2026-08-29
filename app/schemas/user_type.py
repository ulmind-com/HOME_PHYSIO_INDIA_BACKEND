"""Schemas for User Types."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import IdTimestampSchema


class UserTypeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: Optional[str] = None
    description: str = ""
    is_core: bool = False  # Normally admin creates non-core


class UserTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None


class UserTypeResponse(IdTimestampSchema):
    name: str
    slug: str
    description: str
    is_core: bool
