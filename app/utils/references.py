"""Human-friendly reference-code generation (bookings, rentals, applications)."""

from __future__ import annotations

import datetime as dt
import secrets
import string

_ALPHABET = string.ascii_uppercase + string.digits


def generate_reference(prefix: str = "NHH", length: int = 5) -> str:
    """Generate a reference like ``NHH-20260728-A1B2C``.

    Combines a date component with a cryptographically-random suffix, giving a
    readable yet collision-resistant identifier.
    """
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(length))
    return f"{prefix}-{today}-{suffix}"
