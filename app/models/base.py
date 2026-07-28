"""Base document mixins and reusable embedded sub-documents."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, Field


def utcnow() -> dt.datetime:
    """Timezone-aware UTC now (used as default factory for timestamps)."""
    return dt.datetime.now(dt.timezone.utc)


class TimestampedDocument(Document):
    """Base for all documents providing created/updated timestamps.

    ``touch()`` should be called by the repository layer before saving an
    update so ``updated_at`` always reflects the last mutation.
    """

    created_at: dt.datetime = Field(default_factory=utcnow)
    updated_at: dt.datetime = Field(default_factory=utcnow)

    def touch(self) -> None:
        """Refresh the ``updated_at`` timestamp."""
        self.updated_at = utcnow()


class ImageAsset(BaseModel):
    """A Cloudinary-backed image reference."""

    url: str
    public_id: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    alt: Optional[str] = None


class FileAsset(BaseModel):
    """A generic Cloudinary-backed file reference (resume, document, video)."""

    url: str
    public_id: Optional[str] = None
    resource_type: Optional[str] = None
    format: Optional[str] = None
    bytes: Optional[int] = None
    original_filename: Optional[str] = None


class SEOMeta(BaseModel):
    """Embedded SEO metadata attached to public content entities."""

    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    og_image: Optional[str] = None
    schema_markup: Optional[str] = None
