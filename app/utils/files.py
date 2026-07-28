"""Upload validation helpers."""

from __future__ import annotations

from typing import Iterable

from fastapi import UploadFile

from app.core.exceptions import BadRequestException

# Size limits (bytes).
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_BYTES = 100 * 1024 * 1024  # 100 MB

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
DOC_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}


async def read_validated_upload(
    file: UploadFile,
    allowed_types: Iterable[str],
    max_bytes: int,
) -> bytes:
    """Read an ``UploadFile`` fully, enforcing content-type and size limits.

    Returns the file bytes or raises :class:`BadRequestException`.
    """
    allowed = set(allowed_types)
    if file.content_type not in allowed:
        raise BadRequestException(
            f"Unsupported file type '{file.content_type}'. "
            f"Allowed: {', '.join(sorted(allowed))}"
        )

    contents = await file.read()
    if not contents:
        raise BadRequestException("Uploaded file is empty")
    if len(contents) > max_bytes:
        raise BadRequestException(
            f"File too large. Maximum size is {max_bytes // (1024 * 1024)} MB"
        )
    return contents
