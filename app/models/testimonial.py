"""Testimonial document."""

from __future__ import annotations

from typing import Optional

import pymongo
from pydantic import Field

from app.models.base import ImageAsset, TimestampedDocument


class Testimonial(TimestampedDocument):
    """A patient / client testimonial."""

    patient_name: str
    designation: Optional[str] = None
    photo: Optional[ImageAsset] = None
    message: str
    rating: int = Field(default=5, ge=1, le=5)

    is_featured: bool = False
    order: int = 0
    is_active: bool = True

    class Settings:
        name = "testimonials"
        indexes = [
            [("is_active", pymongo.ASCENDING)],
            [("is_featured", pymongo.ASCENDING)],
            [("order", pymongo.ASCENDING)],
        ]
