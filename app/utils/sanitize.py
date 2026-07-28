"""Light input sanitisation helpers.

The API stores data that may later be rendered by a frontend. We strip control
characters and collapse whitespace, and neutralise obvious HTML tag injection
for plain-text fields. Rich-text (blog content) is intentionally left intact
and must be sanitised on render by the frontend.
"""

from __future__ import annotations

import html
import re
from typing import Optional

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")


def sanitize_str(value: Optional[str], collapse_whitespace: bool = True) -> Optional[str]:
    """Strip control chars and (optionally) collapse whitespace.

    Returns ``None`` unchanged so it is safe to apply to optional fields.
    """
    if value is None:
        return None
    cleaned = _CONTROL_CHARS.sub("", value).strip()
    if collapse_whitespace:
        cleaned = _WHITESPACE.sub(" ", cleaned)
    return cleaned


def escape_html(value: Optional[str]) -> Optional[str]:
    """HTML-escape a plain-text value to neutralise tag injection."""
    if value is None:
        return None
    return html.escape(value, quote=True)
