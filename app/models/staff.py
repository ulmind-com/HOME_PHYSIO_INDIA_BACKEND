"""Staff member document."""

from __future__ import annotations

from typing import Optional

import pymongo
from pydantic import Field, model_validator

from app.models.base import ImageAsset, TimestampedDocument


class StaffMember(TimestampedDocument):
    """A staff member (nurse, attendant, physiotherapist, etc.)."""

    name: str
    photo: Optional[ImageAsset] = None
    category: str  # e.g. "Health Attendant", "Nurse", "Physiotherapist", "Nanny", "Japa"
    rating: float = Field(default=5.0, ge=1.0, le=5.0)
    service_label: str = ""  # e.g. "24 hours Health Attendant"
    price_7_days: Optional[int] = None
    price_15_days: Optional[int] = None
    price_30_days: Optional[int] = None
    experience: Optional[str] = None  # e.g. "3 years"
    bio: Optional[str] = None

    is_featured: bool = False
    is_active: bool = True
    order: int = 0

    @model_validator(mode="before")
    @classmethod
    def _drop_null_defaults(cls, data: object) -> object:
        """Legacy/imported staff documents sometimes store an explicit ``null``
        for fields that are non-nullable with a default (e.g. ``order: null``).
        Loading such a document used to raise and 500 the whole /staff list, so
        drop those nulls and let the field default apply."""
        if isinstance(data, dict):
            for field in ("order", "rating", "service_label", "is_featured", "is_active"):
                if field in data and data[field] is None:
                    data.pop(field)
        return data

    class Settings:
        name = "staff_members"
        indexes = [
            [("category", pymongo.ASCENDING)],
            [("is_active", pymongo.ASCENDING)],
            [("is_featured", pymongo.ASCENDING)],
            [("order", pymongo.ASCENDING)],
        ]
