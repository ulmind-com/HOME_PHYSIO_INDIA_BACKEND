"""Email & Password registration and OTP verification flows."""



import datetime as dt
import logging
import random
import string
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, Field

from app.config import settings
from app.core.exceptions import BadRequestException
from app.core.limiter import limiter
from app.core.responses import success_response
from app.core.security import hash_password
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserResponse
from app.services.auth_service import auth_service
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Email Authentication"])

_users: BaseRepository[User] = BaseRepository(User)


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone: str = Field(..., min_length=10, description="Mandatory phone number")


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ResendOtpRequest(BaseModel):
    email: EmailStr


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _generate_otp() -> str:
    """Generate a 6-digit numeric OTP."""
    return "".join(random.choices(string.digits, k=6))


@router.post("/register", summary="Register a new patient account")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register_account(request: Request, payload: RegisterRequest) -> dict:
    """Register an account and send a verification OTP via email."""
    email_lower = payload.email.lower().strip()
    
    existing = await _users.find_one({"email": email_lower})
    if existing:
        if existing.is_email_verified:
            raise BadRequestException("User with this email already exists.")
        else:
            # User exists but not verified. We can resend OTP.
            user = existing
    else:
        user = User(
            name=payload.name.strip(),
            email=email_lower,
            hashed_password=hash_password(payload.password),
            phone=payload.phone.strip(),
            is_email_verified=False,
            role="patient",
            user_type="patient",
            is_active=True,
        )
    
    otp = _generate_otp()
    user.email_verification_otp = otp
    user.otp_expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10)
    
    if existing:
        await user.save()
    else:
        await _users.create(user)
        
    await email_service.send_verification_otp(user.email, otp)
    
    return success_response(
        message="Registration successful. Please verify your email with the OTP sent.",
    )


@router.post("/verify-email", summary="Verify email using OTP")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def verify_email(request: Request, payload: VerifyEmailRequest) -> dict:
    """Verify the 6-digit OTP and issue JWT tokens."""
    email_lower = payload.email.lower().strip()
    user = await _users.find_one({"email": email_lower})
    
    if not user:
        raise BadRequestException("User not found.")
    
    if user.is_email_verified:
        raise BadRequestException("Email is already verified.")
        
    if user.email_verification_otp != payload.otp:
        raise BadRequestException("Invalid OTP.")
        
    if not user.otp_expires_at or user.otp_expires_at < dt.datetime.now(dt.timezone.utc):
        raise BadRequestException("OTP has expired. Please request a new one.")
        
    # Mark as verified and clear OTP fields
    user.is_email_verified = True
    user.email_verification_otp = None
    user.otp_expires_at = None
    await user.save()
    
    # Auto login the user
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
        message="Email verified and logged in successfully.",
    )


@router.post("/resend-otp", summary="Resend email verification OTP")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def resend_otp(request: Request, payload: ResendOtpRequest) -> dict:
    """Resend a new 6-digit OTP to the unverified email."""
    email_lower = payload.email.lower().strip()
    user = await _users.find_one({"email": email_lower})
    
    if not user:
        # Don't reveal if user exists or not for security
        return success_response(message="If the email is registered and unverified, an OTP has been sent.")
        
    if user.is_email_verified:
        return success_response(message="Email is already verified.")
        
    otp = _generate_otp()
    user.email_verification_otp = otp
    user.otp_expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10)
    await user.save()
    
    await email_service.send_verification_otp(user.email, otp)
    
    return success_response(message="If the email is registered and unverified, an OTP has been sent.")
