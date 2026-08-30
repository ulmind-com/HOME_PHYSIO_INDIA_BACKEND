"""Phone-number + OTP authentication via Firebase.

The client performs Firebase Phone Auth on the frontend, then sends
the resulting Firebase ``idToken`` to this endpoint. The backend verifies
it with the Firebase Admin SDK, finds or creates the patient in MongoDB,
and issues our own JWT access + refresh token pair.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from fastapi import APIRouter, Request

from app.config import settings
from app.core.exceptions import BadRequestException, UnauthorizedException
from app.core.limiter import limiter
from app.core.responses import success_response
from app.core.security import create_access_token, create_refresh_token
from app.models.token import RefreshToken
from app.models.user import AdminSession, User
from app.repositories.base import BaseRepository
from app.schemas.user import UserResponse
from app.services.activity_service import activity_service
from app.services.firebase_service import verify_firebase_token
from app.models.enums import ActivityAction
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Phone Authentication"])

_users: BaseRepository[User] = BaseRepository(User)
_tokens: BaseRepository[RefreshToken] = BaseRepository(RefreshToken)
_sessions: BaseRepository[AdminSession] = BaseRepository(AdminSession)


class PhoneLoginRequest(BaseModel):
    """Request body for phone login — the Firebase idToken."""
    id_token: str = Field(..., min_length=20, description="Firebase ID token from client")


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/phone-login", summary="Patient phone login via Firebase OTP")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def phone_login(request: Request, payload: PhoneLoginRequest) -> dict:
    """Verify a Firebase ID token, find-or-create the patient, and issue JWTs.

    Flow:
    1. Client completes Firebase Phone Auth (reCAPTCHA + OTP).
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
    phone_number: str = decoded.get("phone_number", "")

    if not firebase_uid:
        raise BadRequestException("Firebase token missing uid")
    if not phone_number:
        raise BadRequestException("Firebase token missing phone_number")

    # ---- Step 2: Find or create user (upsert pattern) ----
    user = await _users.find_one({"firebase_uid": firebase_uid})

    if user is None:
        # Also check by phone number in case admin created the user earlier
        user = await _users.find_one({"phone": phone_number})

    if user is None:
        # Create a new Patient user
        # Generate a unique email placeholder (patients don't need real emails for phone auth)
        placeholder_email = f"patient_{phone_number.replace('+', '')}@homephysioindia.local"

        user = User(
            name=f"Patient ({phone_number})",
            email=placeholder_email,
            hashed_password="",  # No password for phone-auth users
            phone=phone_number,
            firebase_uid=firebase_uid,
            role="patient",
            user_type="patient",
            is_active=True,
            is_superuser=False,
        )
        await _users.create(user)
        logger.info("Created new patient user: %s (phone: %s)", user.id, phone_number)
    else:
        # Link the Firebase UID if not already linked
        update_data = {}
        if not user.firebase_uid:
            update_data["firebase_uid"] = firebase_uid
        if not user.phone:
            update_data["phone"] = phone_number
        if update_data:
            await _users.update(user, update_data)

    if not user.is_active:
        raise UnauthorizedException("Your account is disabled")

    # ---- Step 3: Issue our own JWT tokens ----
    user_id = str(user.id)
    claims = {"role": user.role, "email": user.email, "user_type": user.user_type}

    access_token, _, _ = create_access_token(user_id, claims)
    refresh_token, jti, expires_at = create_refresh_token(user_id)

    ip = _client_ip(request)
    ua = request.headers.get("User-Agent")

    await _tokens.create(
        RefreshToken(
            jti=jti,
            user_id=user_id,
            expires_at=expires_at,
            ip_address=ip,
            user_agent=ua,
        )
    )
    await _sessions.create(
        AdminSession(
            user_id=user_id,
            user_email=user.email,
            refresh_token_jti=jti,
            ip_address=ip,
            user_agent=ua,
        )
    )

    user.last_login_at = dt.datetime.now(dt.timezone.utc)
    await user.save()

    await activity_service.log(
        ActivityAction.LOGIN,
        "auth",
        user_id=user_id,
        user_email=user.email,
        description=f"Phone login: {phone_number}",
        ip_address=ip,
        user_agent=ua,
    )

    return success_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
        },
        message="Phone login successful",
    )
