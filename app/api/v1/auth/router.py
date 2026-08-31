"""Authentication endpoints: login, refresh, logout, password flows, profile."""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from app.config import settings
from app.core.limiter import limiter
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, get_actor, get_current_active_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResetPasswordRequest,
)
from app.schemas.user import ProfileUpdate, UserResponse
from app.services.auth_service import auth_service
from app.api.v1.auth.google_auth import router as google_router
from app.api.v1.auth.email_auth import router as email_router

router = APIRouter(prefix="/auth", tags=["Authentication"])
router.include_router(google_router)
router.include_router(email_router)


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", summary="Admin login")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(request: Request, response: Response, payload: LoginRequest) -> dict:
    """Authenticate an admin and return an access + refresh token pair."""
    user = await auth_service.authenticate(payload.email, payload.password)
    access, refresh = await auth_service.issue_tokens(
        user,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return success_response(
        data={
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
        },
        message="Login successful",
    )


@router.post("/refresh", summary="Refresh access token")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def refresh(request: Request, response: Response, payload: RefreshRequest) -> dict:
    """Rotate a refresh token and issue a new access + refresh pair."""
    access, refresh_token = await auth_service.refresh(
        payload.refresh_token,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return success_response(
        data={
            "access_token": access,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        },
        message="Token refreshed",
    )


@router.post("/logout", summary="Logout (revoke refresh token)")
async def logout(
    payload: LogoutRequest,
    _: User = Depends(get_current_active_user),
) -> dict:
    """Revoke the supplied refresh token and end its session."""
    await auth_service.logout(payload.refresh_token)
    return success_response(message="Logged out successfully")


@router.post("/change-password", summary="Change password")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    actor: ActorContext = Depends(get_actor),
) -> dict:
    """Change the authenticated user's password."""
    await auth_service.change_password(
        actor.user, payload.current_password, payload.new_password
    )
    return success_response(message="Password changed successfully")


@router.post("/forgot-password", summary="Request password reset email")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def forgot_password(
    request: Request,
    response: Response,
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """Send a password-reset link if the email exists (always 200)."""
    background_tasks.add_task(auth_service.forgot_password, payload.email)
    return success_response(
        message="If the email exists, a reset link has been sent"
    )


@router.post("/reset-password", summary="Reset password with token")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def reset_password(request: Request, payload: ResetPasswordRequest) -> dict:
    """Complete a password reset using the emailed token."""
    await auth_service.reset_password(payload.token, payload.new_password)
    return success_response(message="Password has been reset successfully")


@router.get("/me", summary="Get current profile")
async def me(user: User = Depends(get_current_active_user)) -> dict:
    """Return the authenticated user's profile."""
    return success_response(
        data=UserResponse.model_validate(user).model_dump(mode="json"),
        message="Profile fetched",
    )


@router.put("/me", summary="Update current profile")
async def update_me(
    payload: ProfileUpdate,
    user: User = Depends(get_current_active_user),
) -> dict:
    """Update the authenticated user's own profile fields."""
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(user, key, value)
    user.touch()
    await user.save()
    return success_response(
        data=UserResponse.model_validate(user).model_dump(mode="json"),
        message="Profile updated",
    )
