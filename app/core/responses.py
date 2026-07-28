"""Standard API response envelope.

Every endpoint returns the same JSON shape::

    {
        "success": true,
        "message": "",
        "data": {},
        "errors": null
    }
"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Generic success/error response envelope used across the whole API."""

    success: bool = True
    message: str = ""
    data: Optional[T] = None
    errors: Optional[Any] = None


class PaginationMeta(BaseModel):
    """Pagination metadata returned alongside list responses."""

    total: int = Field(..., description="Total number of matching records")
    page: int = Field(..., description="Current 1-based page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether a next page exists")
    has_prev: bool = Field(..., description="Whether a previous page exists")


class PaginatedData(BaseModel, Generic[T]):
    """Container for a page of items plus pagination metadata."""

    items: List[T]
    pagination: PaginationMeta


def success_response(
    data: Any = None,
    message: str = "Request successful",
) -> dict:
    """Build a success envelope as a plain dict (fast JSON serialisation)."""
    return {"success": True, "message": message, "data": data, "errors": None}


def error_response(
    message: str = "Request failed",
    errors: Any = None,
) -> dict:
    """Build an error envelope as a plain dict."""
    return {"success": False, "message": message, "data": None, "errors": errors}


def build_pagination_meta(total: int, page: int, page_size: int) -> PaginationMeta:
    """Compute pagination metadata from a total count and page settings."""
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return PaginationMeta(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
