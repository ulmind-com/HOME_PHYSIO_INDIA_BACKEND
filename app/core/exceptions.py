"""Custom application exceptions.

These carry an HTTP status code plus a human friendly message and optional
structured ``errors`` payload. A single global handler (see
``app.core.handlers``) turns them into the standard response envelope.
"""

from __future__ import annotations

from typing import Any, Optional


class AppException(Exception):
    """Base class for all application-specific exceptions."""

    status_code: int = 500
    message: str = "Internal server error"

    def __init__(
        self,
        message: Optional[str] = None,
        errors: Any = None,
        status_code: Optional[int] = None,
    ) -> None:
        self.message = message or self.message
        self.errors = errors
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class BadRequestException(AppException):
    """400 - the request was malformed or failed a business rule."""

    status_code = 400
    message = "Bad request"


class UnauthorizedException(AppException):
    """401 - authentication is required or failed."""

    status_code = 401
    message = "Authentication required"


class ForbiddenException(AppException):
    """403 - authenticated but lacking the required permission/role."""

    status_code = 403
    message = "You do not have permission to perform this action"


class NotFoundException(AppException):
    """404 - the requested resource does not exist."""

    status_code = 404
    message = "Resource not found"


class ConflictException(AppException):
    """409 - the request conflicts with the current state (e.g. duplicate)."""

    status_code = 409
    message = "Resource already exists"


class ValidationException(AppException):
    """422 - semantic validation failure."""

    status_code = 422
    message = "Validation failed"


class RateLimitException(AppException):
    """429 - too many requests."""

    status_code = 429
    message = "Too many requests, please slow down"


class ServiceUnavailableException(AppException):
    """503 - a downstream dependency (email, storage, db) is unavailable."""

    status_code = 503
    message = "Service temporarily unavailable"
