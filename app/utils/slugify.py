"""Slug generation helpers."""

from __future__ import annotations

from typing import Awaitable, Callable

from slugify import slugify


async def unique_slug(
    value: str,
    exists: Callable[[str], Awaitable[bool]],
    max_length: int = 80,
) -> str:
    """Generate a URL-safe slug that is unique per ``exists`` predicate.

    Args:
        value: The source text to slugify.
        exists: Async predicate returning ``True`` if a slug is already taken.
        max_length: Maximum slug length.

    Returns:
        A unique slug, appending ``-2``, ``-3`` ... on collision.
    """
    base = slugify(value, max_length=max_length) or "item"
    candidate = base
    counter = 2
    while await exists(candidate):
        suffix = f"-{counter}"
        candidate = f"{base[: max_length - len(suffix)]}{suffix}"
        counter += 1
    return candidate
