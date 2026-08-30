"""Firebase Admin SDK service for verifying Firebase ID tokens.

This service initializes the Firebase Admin SDK and provides a method
to verify ID tokens received from the frontend after Firebase Phone Auth.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_firebase_app = None


def _ensure_initialized() -> None:
    """Lazily initialize the Firebase Admin SDK (once)."""
    global _firebase_app
    if _firebase_app is not None:
        return

    if not settings.firebase_enabled:
        logger.warning("Firebase is not configured — phone auth will not work")
        return

    try:
        import firebase_admin  # type: ignore[import-untyped]
        from firebase_admin import credentials  # type: ignore[import-untyped]

        if settings.FIREBASE_SERVICE_ACCOUNT_PATH:
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            # Use project ID only (works for ID token verification without
            # needing a full service account key in development).
            _firebase_app = firebase_admin.initialize_app(
                options={"projectId": settings.FIREBASE_PROJECT_ID}
            )
        logger.info("Firebase Admin SDK initialized (project: %s)", settings.FIREBASE_PROJECT_ID)
    except Exception as exc:
        logger.error("Failed to initialise Firebase Admin SDK: %s", exc)
        raise


async def verify_firebase_token(id_token: str) -> Dict[str, Any]:
    """Verify a Firebase ID token and return the decoded claims.

    Returns a dict containing at least ``uid`` and ``phone_number``.

    Raises
    ------
    ValueError
        If Firebase is not configured or the token is invalid / expired.
    """
    _ensure_initialized()

    if _firebase_app is None:
        raise ValueError("Firebase Admin SDK is not initialised")

    from firebase_admin import auth as firebase_auth  # type: ignore[import-untyped]

    import asyncio

    try:
        decoded = await asyncio.to_thread(
            firebase_auth.verify_id_token, id_token, check_revoked=True
        )
        return decoded
    except firebase_auth.RevokedIdTokenError:
        raise ValueError("Firebase token has been revoked")
    except firebase_auth.ExpiredIdTokenError:
        raise ValueError("Firebase token has expired")
    except firebase_auth.InvalidIdTokenError:
        raise ValueError("Invalid Firebase token")
    except Exception as exc:
        logger.error("Firebase token verification failed: %s", exc)
        raise ValueError(f"Firebase token verification error: {exc}")
