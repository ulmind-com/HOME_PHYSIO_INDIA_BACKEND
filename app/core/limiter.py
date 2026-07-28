"""SlowAPI rate limiter singleton.

Keyed by client IP. Applied globally via the app state and per-route through
the ``@limiter.limit(...)`` decorator on sensitive endpoints (auth, contact).
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    headers_enabled=True,
)
