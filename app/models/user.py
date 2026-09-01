"""User and admin session documents."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

import pymongo
from beanie import Indexed
from pydantic import EmailStr, Field

from app.models.base import ImageAsset, TimestampedDocument, utcnow


class User(TimestampedDocument):
    """An administrative / staff user of the platform.

    The platform is admin-facing only, so every user is a back-office account
    guarded by role-based access control (see :mod:`app.models.rbac`).
    """

    name: str
    email: Indexed(EmailStr, unique=True)  # type: ignore[valid-type]
    hashed_password: str = ""  # Empty for phone-auth-only users
    phone: Optional[str] = None
    address: Optional[str] = None
    avatar: Optional[ImageAsset] = None
    
    # Therapist specific fields
    specialization: Optional[str] = None
    experience_years: Optional[int] = None

    # Google OAuth linkage
    google_uid: Optional[str] = None
    
    # Email Verification
    is_email_verified: bool = False
    email_verification_otp: Optional[str] = None
    otp_expires_at: Optional[dt.datetime] = None

    # RBAC: a single role slug plus any directly-granted extra permissions.
    role: str = "admin"
    extra_permissions: List[str] = Field(default_factory=list)
    user_type: str = "admin"  # Reference to UserType slug

    is_active: bool = True
    is_superuser: bool = False

    last_login_at: Optional[dt.datetime] = None

    # Password reset bookkeeping (token jti is single-use).
    reset_token_jti: Optional[str] = None

    class Settings:
        name = "users"
        indexes = [
            [("email", pymongo.ASCENDING)],
            [("role", pymongo.ASCENDING)],
            [("is_active", pymongo.ASCENDING)],
            [("google_uid", pymongo.ASCENDING)],
        ]


class AdminSession(TimestampedDocument):
    """A record of an authenticated admin session for auditing/tracking."""

    user_id: str
    user_email: str
    refresh_token_jti: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True
    last_seen_at: dt.datetime = Field(default_factory=utcnow)
    revoked_at: Optional[dt.datetime] = None

    class Settings:
        name = "admin_sessions"
        indexes = [
            [("user_id", pymongo.ASCENDING)],
            [("refresh_token_jti", pymongo.ASCENDING)],
            [("is_active", pymongo.ASCENDING)],
        ]
