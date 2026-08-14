"""Upload validation helpers."""

from __future__ import annotations

import os
from typing import Iterable, Optional

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

# Allowed filename extensions for resume/document uploads.
DOC_EXTENSIONS = {".pdf", ".doc", ".docx"}

# Real file-header signatures ("magic bytes") for the document formats we accept.
# A renamed executable, script or archive will not carry any of these, so it is
# rejected even when the client spoofs the ``Content-Type`` header.
_DOC_SIGNATURES = (
    b"%PDF-",  # PDF
    b"PK\x03\x04",  # DOCX (OOXML — a ZIP container)
    b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",  # legacy .doc (OLE2 compound file)
)


def _extension(filename: Optional[str]) -> str:
    return os.path.splitext(filename or "")[1].lower()


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


async def read_validated_document(file: UploadFile, max_bytes: int) -> bytes:
    """Read a resume/document upload with defence-in-depth validation.

    Enforces, in order: allowed extension, allowed MIME type, size limit, and —
    crucially — that the real file header matches a genuine PDF/DOC/DOCX. This
    blocks malicious files (executables, scripts, HTML) that merely spoof the
    filename or ``Content-Type``.
    """
    if _extension(file.filename) not in DOC_EXTENSIONS:
        raise BadRequestException(
            "Only PDF or Word documents (.pdf, .doc, .docx) are allowed"
        )
    contents = await read_validated_upload(file, DOC_TYPES, max_bytes)
    if not contents.startswith(_DOC_SIGNATURES):
        raise BadRequestException(
            "File content is not a valid PDF or Word document"
        )
    return contents
