"""Reusable pagination, sorting and search query parameters."""

from __future__ import annotations

from typing import Optional

from fastapi import Query
from pydantic import BaseModel


class PaginationParams(BaseModel):
    """Common list query parameters injected via FastAPI dependency."""

    page: int = 1
    page_size: int = 10
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = "desc"

    @property
    def skip(self) -> int:
        """Number of documents to skip for the current page."""
        return (self.page - 1) * self.page_size

    @property
    def sort_direction(self) -> int:
        """Mongo sort direction (1 asc / -1 desc)."""
        return 1 if self.sort_order.lower() == "asc" else -1


def pagination_params(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
    search: Optional[str] = Query(None, description="Free-text search term"),
    sort_by: Optional[str] = Query(None, description="Field name to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="asc | desc"),
) -> PaginationParams:
    """FastAPI dependency returning validated pagination parameters."""
    return PaginationParams(
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
