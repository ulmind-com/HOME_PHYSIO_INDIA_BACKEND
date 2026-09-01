"""User and RBAC schemas."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.base import ImageAsset, FileAsset
from app.schemas.common import IdTimestampSchema

class TherapistDocumentCreate(BaseModel):
    title: str = Field(..., max_length=100)
    file: FileAsset

class TherapistDocumentResponse(BaseModel):
    id: str
    title: str
    file: FileAsset
    is_verified: bool
    uploaded_at: dt.datetime
    verified_at: Optional[dt.datetime] = None

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
    specialization: Optional[str] = Field(None, max_length=120)
    experience_years: Optional[int] = Field(None, ge=0, le=60)
    qualification: Optional[str] = None
    therapist_tier: Optional[str] = None


class UserUpdate(BaseModel):
    """Payload for updating a user (all fields optional)."""

    name: Optional[str] = Field(None, min_length=2, max_length=120)
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = None
    extra_permissions: Optional[List[str]] = None
    user_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    specialization: Optional[str] = Field(None, max_length=120)
    experience_years: Optional[int] = Field(None, ge=0, le=60)
    qualification: Optional[str] = None
    therapist_tier: Optional[str] = None


class TherapistVerificationUpdate(BaseModel):
    """Approve or reject a therapist's registration (admin only)."""

    verification_status: str
    therapist_tier: Optional[str] = None
    rejection_reason: Optional[str] = Field(None, max_length=500)


class UserResponse(IdTimestampSchema):
    """Safe user representation (never exposes the password hash)."""

    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    avatar: Optional[ImageAsset] = None
    age: Optional[int] = None
    pincode: Optional[str] = None
    medical_condition: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: Optional[int] = None
    qualification: Optional[str] = None
    therapist_tier: Optional[str] = None
    verification_status: str = "approved"
    documents: List[TherapistDocumentResponse] = Field(default_factory=list)
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
    age: Optional[int] = Field(None, ge=0, le=120)
    pincode: Optional[str] = Field(None, min_length=4, max_length=10)
    medical_condition: Optional[str] = Field(None, max_length=2000)


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
