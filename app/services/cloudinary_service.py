"""Cloudinary upload/delete integration.

Wraps the synchronous Cloudinary SDK in a thread executor so it never blocks
the event loop, and normalises responses into our :class:`ImageAsset` /
:class:`FileAsset` sub-documents.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import cloudinary
import cloudinary.uploader

from app.config import settings
from app.core.exceptions import ServiceUnavailableException
from app.core.logging import get_logger
from app.models.base import FileAsset, ImageAsset

logger = get_logger(__name__)


class CloudinaryService:
    """Async-friendly wrapper around the Cloudinary SDK."""

    def __init__(self) -> None:
        self._configured = settings.cloudinary_enabled
        if self._configured:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True,
            )
        else:
            logger.warning("Cloudinary is not configured; uploads will fail")

    def _ensure_configured(self) -> None:
        if not self._configured:
            raise ServiceUnavailableException("File storage (Cloudinary) is not configured")

    async def upload_image(
        self,
        file_bytes: bytes,
        folder: str = "home_physio_india/images",
        public_id: Optional[str] = None,
    ) -> ImageAsset:
        """Upload an image with automatic format/quality optimisation."""
        result = await self._upload(
            file_bytes,
            folder=folder,
            public_id=public_id,
            resource_type="image",
            allowed_formats=["jpg", "png", "webp", "gif", "jpeg"],
            transformation=[{"quality": "auto", "fetch_format": "auto"}],
        )
        return ImageAsset(
            url=result["secure_url"],
            public_id=result["public_id"],
            width=result.get("width"),
            height=result.get("height"),
            format=result.get("format"),
        )

    async def upload_file(
        self,
        file_bytes: bytes,
        folder: str = "home_physio_india/files",
        resource_type: str = "auto",
        public_id: Optional[str] = None,
        original_filename: Optional[str] = None,
    ) -> FileAsset:
        """Upload an arbitrary file (resume, document, video)."""
        result = await self._upload(
            file_bytes,
            folder=folder,
            public_id=public_id,
            resource_type=resource_type,
            allowed_formats=["pdf", "doc", "docx", "mp4", "webm", "mov", "avi", "qt"],
        )
        return FileAsset(
            url=result["secure_url"],
            public_id=result["public_id"],
            resource_type=result.get("resource_type"),
            format=result.get("format"),
            bytes=result.get("bytes"),
            original_filename=original_filename,
        )

    async def delete(self, public_id: str, resource_type: str = "image") -> bool:
        """Delete an asset by its public id. Returns ``True`` on success."""
        self._ensure_configured()
        try:
            result = await asyncio.to_thread(
                cloudinary.uploader.destroy, public_id, resource_type=resource_type
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Cloudinary delete failed", extra={"public_id": public_id})
            raise ServiceUnavailableException("Failed to delete file") from exc
        return result.get("result") == "ok"

    async def _upload(self, file_bytes: bytes, **options: Any) -> Dict[str, Any]:
        self._ensure_configured()
        try:
            return await asyncio.to_thread(
                cloudinary.uploader.upload, file_bytes, **options
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Cloudinary upload failed", extra={"error": str(exc)})
            raise ServiceUnavailableException("Failed to upload file") from exc


# Module-level singleton (dependency-injectable via app.dependencies).
cloudinary_service = CloudinaryService()
