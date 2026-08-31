"""Google OAuth authentication via Firebase.

The client performs Google Sign-In on the frontend via Firebase SDK, then sends
the resulting Firebase ``idToken`` to this endpoint. The backend verifies
it with the Firebase Admin SDK, finds or creates the patient in MongoDB,
and issues our own JWT access + refresh token pair.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.core.exceptions import BadRequestException, UnauthorizedException
from app.core.limiter import limiter
from app.core.responses import success_response
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserResponse
from app.services.auth_service import auth_service
from app.services.firebase_service import verify_firebase_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Google Authentication"])

_users: BaseRepository[User] = BaseRepository(User)


class GoogleLoginRequest(BaseModel):
    """Request body for Google login — the Firebase idToken."""
    id_token: str = Field(..., min_length=20, description="Firebase ID token from client")
    phone: Optional[str] = Field(None, description="Mandatory for new registrations via Google")


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/google-login", summary="Patient Google login via Firebase")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def google_login(request: Request, payload: GoogleLoginRequest) -> dict:
    """Verify a Firebase ID token (Google), find-or-create the patient, and issue JWTs.

    Flow:
    1. Client completes Google Sign-In via Firebase Auth.
    2. Client sends the Firebase ``idToken`` to this endpoint.
    3. Backend verifies the token with Firebase Admin SDK.
    4. Backend finds or creates a ``User`` document with ``user_type='patient'``.
    5. Backend issues its own JWT access + refresh token pair.
    """
    # ---- Step 1: Verify Firebase token ----
    try:
        decoded = await verify_firebase_token(payload.id_token)
    except ValueError as exc:
        raise UnauthorizedException(str(exc))

    firebase_uid: str = decoded.get("uid", "")
    email: str = decoded.get("email", "")
    name: str = decoded.get("name", "")

    if not firebase_uid:
        raise BadRequestException("Firebase token missing uid")
    if not email:
        raise BadRequestException("Firebase token missing email")

    # ---- Step 2: Find or create user (upsert pattern) ----
    user = await _users.find_one({"email": email.lower()})

    if user is None:
        if not payload.phone:
            # For new users, phone is mandatory. 
            # Frontend must intercept this and ask for phone, then retry.
            raise BadRequestException("Phone number is required for new registration.")
            
        # Create a new Patient user
        user = User(
            name=name or "Patient",
            email=email.lower(),
            hashed_password="",  # No password for Google-auth users
            phone=payload.phone.strip(),
            google_uid=firebase_uid,
            is_email_verified=True,  # Google verifies email
            role="patient",
            user_type="patient",
            is_active=True,
            is_superuser=False,
        )
        await _users.create(user)
        logger.info("Created new patient user via Google: %s (%s)", user.id, email)
    else:
        # Link the Google UID if not already linked
        update_data = {}
        if not user.google_uid:
            update_data["google_uid"] = firebase_uid
        # If they previously registered manually but didn't verify, verifying now via Google
        if not user.is_email_verified:
            update_data["is_email_verified"] = True
            update_data["email_verification_otp"] = None
            update_data["otp_expires_at"] = None

        if update_data:
            await _users.update(user, update_data)

    if not user.is_active:
        raise UnauthorizedException("Your account is disabled")

    # ---- Step 3: Issue our own JWT tokens ----
    ip = _client_ip(request)
    ua = request.headers.get("User-Agent")

    access_token, refresh_token = await auth_service.issue_tokens(user, ip_address=ip, user_agent=ua)

    return success_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
        },
        message="Google login successful",
    )
