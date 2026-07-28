"""Security primitives: password hashing and JWT creation/verification."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.exceptions import UnauthorizedException

# bcrypt password hashing context.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token type discriminators embedded in the JWT payload.
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
RESET_TOKEN_TYPE = "reset"


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        return False


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: dt.timedelta,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> tuple[str, str, dt.datetime]:
    """Create a signed JWT.

    Returns a tuple of ``(encoded_token, jti, expires_at)``.
    """
    issued_at = _now()
    expires_at = issued_at + expires_delta
    jti = uuid.uuid4().hex

    payload: Dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": issued_at,
        "exp": expires_at,
    }
    if extra_claims:
        payload.update(extra_claims)

    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, jti, expires_at


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> tuple[str, str, dt.datetime]:
    """Create a short-lived access token."""
    return _create_token(
        subject,
        ACCESS_TOKEN_TYPE,
        dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims,
    )


def create_refresh_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> tuple[str, str, dt.datetime]:
    """Create a long-lived refresh token."""
    return _create_token(
        subject,
        REFRESH_TOKEN_TYPE,
        dt.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        extra_claims,
    )


def create_reset_token(subject: str) -> tuple[str, str, dt.datetime]:
    """Create a short-lived password reset token."""
    return _create_token(
        subject,
        RESET_TOKEN_TYPE,
        dt.timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
    )


def decode_token(token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
    """Decode and validate a JWT.

    Args:
        token: The encoded JWT string.
        expected_type: If provided, the token ``type`` claim must match.

    Raises:
        UnauthorizedException: If the token is invalid, expired, or the wrong
            type.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:  # expired, bad signature, malformed, ...
        raise UnauthorizedException("Invalid or expired token") from exc

    if expected_type and payload.get("type") != expected_type:
        raise UnauthorizedException("Invalid token type")

    return payload
