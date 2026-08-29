"""User Type document model for categorization."""

from __future__ import annotations

import pymongo
from beanie import Indexed
from pydantic import Field

from app.models.base import TimestampedDocument

class UserType(TimestampedDocument):
    """A dynamic user type categorization."""

    name: str
    slug: Indexed(str, unique=True)  # type: ignore[valid-type]
    description: str = ""
    is_core: bool = False  # True for hardcoded types like Admin and Patient

    class Settings:
        name = "user_types"
        indexes = [
            [("slug", pymongo.ASCENDING)],
        ]
