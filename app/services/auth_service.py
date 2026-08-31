"""Authentication & session business logic.

Handles login, refresh-token rotation, logout (blacklist), password change and
the forgot/reset password flow. Refresh tokens are persisted so they can be
rotated and revoked, giving real session invalidation on top of stateless JWTs.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional, Tuple

from app.config import settings
from app.core.exceptions import (
    BadRequestException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    RESET_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import ActivityAction
from app.models.token import RefreshToken
from app.models.user import AdminSession, User
from app.repositories.base import BaseRepository
from app.services.activity_service import activity_service
from app.services.email_service import email_service


class AuthService:
    """Coordinates authentication, tokens and sessions."""

    def __init__(self) -> None:
        self.users: BaseRepository[User] = BaseRepository(User)
        self.tokens: BaseRepository[RefreshToken] = BaseRepository(RefreshToken)
        self.sessions: BaseRepository[AdminSession] = BaseRepository(AdminSession)

    # ---- Login ---------------------------------------------------------

    async def authenticate(self, email: str, password: str) -> User:
        """Validate credentials and return the user, or raise 401."""
        user = await self.users.find_one({"email": email.lower().strip()})
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedException("Your account is disabled")
        if not user.is_email_verified:
            raise UnauthorizedException("EMAIL_NOT_VERIFIED")
        return user

    async def issue_tokens(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Create and persist an access + refresh token pair for ``user``."""
        user_id = str(user.id)
        claims = {"role": user.role, "email": user.email}

        access_token, _, _ = create_access_token(user_id, claims)
        refresh_token, jti, expires_at = create_refresh_token(user_id)

        await self.tokens.create(
            RefreshToken(
                jti=jti,
                user_id=user_id,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        await self.sessions.create(
            AdminSession(
                user_id=user_id,
                user_email=user.email,
                refresh_token_jti=jti,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )

        user.last_login_at = dt.datetime.now(dt.timezone.utc)
        await user.save()

        await activity_service.log(
            ActivityAction.LOGIN,
            "auth",
            user_id=user_id,
            user_email=user.email,
            description=f"{user.email} logged in",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return access_token, refresh_token

    # ---- Refresh -------------------------------------------------------

    async def refresh(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Rotate a refresh token, returning a fresh access + refresh pair."""
        payload = decode_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        jti = payload.get("jti", "")
        user_id = payload.get("sub", "")

        stored = await self.tokens.find_one({"jti": jti})
        if stored is None or stored.revoked:
            raise UnauthorizedException("Refresh token is no longer valid")

        user = await self.users.get(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedException("User account is unavailable")

        # Issue new pair and mark the old refresh token as rotated.
        access_token, _, _ = create_access_token(
            user_id, {"role": user.role, "email": user.email}
        )
        new_refresh, new_jti, expires_at = create_refresh_token(user_id)

        stored.revoked = True
        stored.revoked_at = dt.datetime.now(dt.timezone.utc)
        stored.replaced_by_jti = new_jti
        await stored.save()

        await self.tokens.create(
            RefreshToken(
                jti=new_jti,
                user_id=user_id,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        return access_token, new_refresh

    # ---- Logout --------------------------------------------------------

    async def logout(self, refresh_token: str) -> None:
        """Revoke (blacklist) a refresh token and close its session."""
        try:
            payload = decode_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        except UnauthorizedException:
            return  # already invalid — nothing to do
        jti = payload.get("jti", "")

        stored = await self.tokens.find_one({"jti": jti})
        if stored and not stored.revoked:
            stored.revoked = True
            stored.revoked_at = dt.datetime.now(dt.timezone.utc)
            await stored.save()

        session = await self.sessions.find_one({"refresh_token_jti": jti})
        if session and session.is_active:
            session.is_active = False
            session.revoked_at = dt.datetime.now(dt.timezone.utc)
            await session.save()

        await activity_service.log(
            ActivityAction.LOGOUT,
            "auth",
            user_id=payload.get("sub"),
            user_email=payload.get("email"),
            description="User logged out",
        )

    async def is_refresh_token_active(self, jti: str) -> bool:
        """Return ``True`` if a refresh token jti is still valid."""
        stored = await self.tokens.find_one({"jti": jti})
        return bool(stored and not stored.revoked)

    # ---- Passwords -----------------------------------------------------

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        """Change ``user``'s password after verifying the current one."""
        if not verify_password(current_password, user.hashed_password):
            raise BadRequestException("Current password is incorrect")
        user.hashed_password = hash_password(new_password)
        user.touch()
        await user.save()
        # Revoke all existing refresh tokens for safety.
        await self._revoke_all_user_tokens(str(user.id))

    async def forgot_password(self, email: str) -> None:
        """Generate a reset token and email a reset link (best-effort)."""
        user = await self.users.find_one({"email": email.lower().strip()})
        # Do not reveal whether the email exists.
        if user is None:
            return
        token, jti, _ = create_reset_token(str(user.id))
        user.reset_token_jti = jti
        await user.save()
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        await email_service.send_password_reset(user.email, reset_link)

    async def reset_password(self, token: str, new_password: str) -> None:
        """Reset a password using a valid single-use reset token."""
        payload = decode_token(token, expected_type=RESET_TOKEN_TYPE)
        user = await self.users.get(payload.get("sub", ""))
        if user is None:
            raise NotFoundException("User not found")
        if user.reset_token_jti != payload.get("jti"):
            raise BadRequestException("This reset link has already been used")

        user.hashed_password = hash_password(new_password)
        user.reset_token_jti = None
        user.touch()
        await user.save()
        await self._revoke_all_user_tokens(str(user.id))

    async def _revoke_all_user_tokens(self, user_id: str) -> None:
        now = dt.datetime.now(dt.timezone.utc)
        await RefreshToken.find({"user_id": user_id, "revoked": False}).update(
            {"$set": {"revoked": True, "revoked_at": now}}
        )
        await AdminSession.find({"user_id": user_id, "is_active": True}).update(
            {"$set": {"is_active": False, "revoked_at": now}}
        )


auth_service = AuthService()
