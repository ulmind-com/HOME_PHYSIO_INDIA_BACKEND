"""Router-level helpers for building consistent responses."""

from __future__ import annotations

from typing import Any, List, Sequence, Type

from pydantic import BaseModel

from app.core.pagination import PaginationParams
from app.core.responses import build_pagination_meta, success_response


def serialize_list(schema: Type[BaseModel], items: Sequence[Any]) -> List[dict]:
    """Convert a list of documents to JSON-ready dicts via a response schema."""
    return [schema.model_validate(item).model_dump(mode="json") for item in items]


def paginated_response(
    schema: Type[BaseModel],
    items: Sequence[Any],
    total: int,
    params: PaginationParams,
    message: str = "Fetched successfully",
) -> dict:
    """Build the standard envelope for a paginated list endpoint."""
    meta = build_pagination_meta(total, params.page, params.page_size)
    return success_response(
        data={
            "items": serialize_list(schema, items),
            "pagination": meta.model_dump(),
        },
        message=message,
    )


def item_response(
    schema: Type[BaseModel],
    item: Any,
    message: str = "Fetched successfully",
) -> dict:
    """Build the standard envelope for a single-item endpoint."""
    return success_response(
        data=schema.model_validate(item).model_dump(mode="json"), message=message
    )
