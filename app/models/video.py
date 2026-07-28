"""Video gallery document."""

from __future__ import annotations

from typing import Optional

import pymongo
from beanie import Indexed

from app.models.base import FileAsset, ImageAsset, TimestampedDocument
from app.models.enums import VideoSource


class Video(TimestampedDocument):
    """A video entry (YouTube link or Cloudinary-hosted file)."""

    title: str
    slug: Indexed(str, unique=True)  # type: ignore[valid-type]
    description: str = ""
    category: Optional[str] = None

    source: VideoSource = VideoSource.YOUTUBE
    youtube_url: Optional[str] = None
    video_file: Optional[FileAsset] = None
    thumbnail: Optional[ImageAsset] = None

    is_featured: bool = False
    order: int = 0
    is_active: bool = True

    class Settings:
        name = "videos"
        indexes = [
            [("slug", pymongo.ASCENDING)],
            [("category", pymongo.ASCENDING)],
            [("is_active", pymongo.ASCENDING)],
            [("order", pymongo.ASCENDING)],
        ]
