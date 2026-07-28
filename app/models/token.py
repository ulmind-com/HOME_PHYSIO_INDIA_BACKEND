"""Refresh token document (persistent store enabling rotation & blacklist)."""

from __future__ import annotations

import datetime as dt
from typing import Optional

import pymongo
from beanie import Indexed

from app.models.base import TimestampedDocument


class RefreshToken(TimestampedDocument):
    """Server-side record of an issued refresh token.

    Storing refresh tokens lets us rotate them on use and revoke (blacklist)
    them on logout, providing real session invalidation on top of stateless
    JWTs.
    """

    jti: Indexed(str, unique=True)  # type: ignore[valid-type]
    user_id: str
    expires_at: dt.datetime
    revoked: bool = False
    revoked_at: Optional[dt.datetime] = None
    replaced_by_jti: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    class Settings:
        name = "refresh_tokens"
        indexes = [
            [("jti", pymongo.ASCENDING)],
            [("user_id", pymongo.ASCENDING)],
            [("revoked", pymongo.ASCENDING)],
            # TTL index: Mongo auto-removes expired tokens.
            pymongo.IndexModel(
                [("expires_at", pymongo.ASCENDING)], expireAfterSeconds=0
            ),
        ]
