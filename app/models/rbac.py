"""Role-Based Access Control documents: roles and permissions."""

from __future__ import annotations

from typing import List

import pymongo
from beanie import Indexed
from pydantic import Field

from app.models.base import TimestampedDocument


class Permission(TimestampedDocument):
    """A granular permission, e.g. ``bookings:create``.

    Permissions follow a ``resource:action`` naming convention which keeps the
    authorization dependency simple and predictable.
    """

    code: Indexed(str, unique=True)  # type: ignore[valid-type]
    name: str
    description: str = ""
    group: str = "general"

    class Settings:
        name = "permissions"


class Role(TimestampedDocument):
    """A named collection of permissions assignable to users."""

    slug: Indexed(str, unique=True)  # type: ignore[valid-type]
    name: str
    description: str = ""
    permissions: List[str] = Field(default_factory=list)
    is_system: bool = False

    class Settings:
        name = "roles"
        indexes = [
            [("slug", pymongo.ASCENDING)],
        ]
