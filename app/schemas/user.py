"""User and RBAC schemas."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.base import ImageAsset
from app.schemas.common import IdTimestampSchema


class UserCreate(BaseModel):
    """Payload for creating an admin/staff user."""

    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=20)
    role: str = "admin"
    extra_permissions: List[str] = Field(default_factory=list)
    user_type: str = "admin"
    is_active: bool = True
    is_superuser: bool = False
    send_credentials_email: bool = False


class UserUpdate(BaseModel):
    """Payload for updating a user (all fields optional)."""

    name: Optional[str] = Field(None, min_length=2, max_length=120)
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = None
    extra_permissions: Optional[List[str]] = None
    user_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserResponse(IdTimestampSchema):
    """Safe user representation (never exposes the password hash)."""

    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    avatar: Optional[ImageAsset] = None
    specialization: Optional[str] = None
    experience_years: Optional[int] = None
    role: str
    extra_permissions: List[str] = Field(default_factory=list)
    user_type: str
    is_active: bool
    is_superuser: bool
    last_login_at: Optional[dt.datetime] = None


class ProfileUpdate(BaseModel):
    """Fields a user may update on their own profile."""

    name: Optional[str] = Field(None, min_length=2, max_length=120)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)


# ---- Roles & permissions ----


class RoleCreate(BaseModel):
    """Create a role."""

    name: str = Field(..., min_length=2, max_length=80)
    slug: Optional[str] = None
    description: str = ""
    permissions: List[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Update a role."""

    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleResponse(IdTimestampSchema):
    """Role representation."""

    slug: str
    name: str
    description: str
    permissions: List[str]
    is_system: bool


class PermissionResponse(IdTimestampSchema):
    """Permission representation."""

    code: str
    name: str
    description: str
    group: str
