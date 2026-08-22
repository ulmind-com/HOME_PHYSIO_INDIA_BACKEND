"""Router-level helpers for building consistent responses."""

from __future__ import annotations

from typing import Any, List, Sequence, Type

from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger
from app.core.pagination import PaginationParams
from app.core.responses import build_pagination_meta, success_response

logger = get_logger(__name__)


def serialize_list(schema: Type[BaseModel], items: Sequence[Any]) -> List[dict]:
    """Convert a list of documents to JSON-ready dicts via a response schema.

    A single malformed document must not take down the whole list endpoint, so
    items that fail validation are skipped (and logged) instead of raising —
    the endpoint still returns every valid record rather than a 500.
    """
    out: List[dict] = []
    for item in items:
        try:
            out.append(schema.model_validate(item).model_dump(mode="json"))
        except ValidationError as exc:
            logger.warning(
                "Skipping document that failed %s validation: %s",
                schema.__name__,
                exc,
                extra={"doc_id": str(getattr(item, "id", None))},
            )
    return out


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
