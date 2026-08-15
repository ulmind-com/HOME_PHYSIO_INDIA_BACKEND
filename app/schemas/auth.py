"""Authentication request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Admin login credentials."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Issued token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access-token lifetime in seconds")


class RefreshRequest(BaseModel):
    """Request a new access token from a refresh token."""

    refresh_token: str = Field(..., min_length=10)


class LogoutRequest(BaseModel):
    """Revoke a refresh token on logout."""

    refresh_token: str = Field(..., min_length=10)


class ChangePasswordRequest(BaseModel):
    """Change the current user's password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        import re
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[\W_]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class ForgotPasswordRequest(BaseModel):
    """Request a password-reset email."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Complete a password reset using the emailed token."""

    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        import re
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[\W_]", v):
            raise ValueError("Password must contain at least one special character")
        return v
