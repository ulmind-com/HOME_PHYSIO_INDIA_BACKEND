"""FAQ document."""

from __future__ import annotations

from typing import Optional

import pymongo

from app.models.base import TimestampedDocument


class FAQ(TimestampedDocument):
    """A frequently-asked-question entry."""

    question: str
    answer: str
    category: Optional[str] = None
    order: int = 0
    is_active: bool = True

    class Settings:
        name = "faqs"
        indexes = [
            [("category", pymongo.ASCENDING)],
            [("is_active", pymongo.ASCENDING)],
            [("order", pymongo.ASCENDING)],
            [("question", pymongo.TEXT), ("answer", pymongo.TEXT)],
        ]
