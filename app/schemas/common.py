"""Shared base schemas and mixins."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ORMSchema(BaseModel):
    """Base response schema that can be built from a Beanie document."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class IdTimestampSchema(ORMSchema):
    """Mixin adding the stringified id and timestamps to response schemas."""

    id: str
    created_at: Optional[dt.datetime] = None
    updated_at: Optional[dt.datetime] = None

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, value: object) -> str:
        """Convert Mongo ObjectId / PydanticObjectId to a plain string."""
        return str(value)


class MessageResponse(BaseModel):
    """Simple ``{"id": ...}`` style acknowledgement payload."""

    id: Optional[str] = None
    detail: Optional[str] = None
