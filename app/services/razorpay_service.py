"""Razorpay order creation and payment verification.

Talks to the Razorpay REST API directly over ``requests`` rather than the
official ``razorpay`` SDK, which pulls in ``pkg_resources`` and breaks on
modern ``setuptools`` releases that no longer bundle it.
"""

from __future__ import annotations

import asyncio
import hmac
import hashlib
from typing import Any, Dict, Optional

import requests

from app.config import settings
from app.core.exceptions import ServiceUnavailableException
from app.core.logging import get_logger

logger = get_logger(__name__)

API_BASE = "https://api.razorpay.com/v1"


class RazorpayService:
    """Thin wrapper around the Razorpay Orders/Payments REST API."""

    def __init__(self) -> None:
        self.enabled = settings.razorpay_enabled
        self._auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise ServiceUnavailableException("Payment gateway is not configured")

    def _sync_create_order(self, amount_rupees: int, receipt: str, notes: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{API_BASE}/orders",
            json={
                "amount": amount_rupees * 100,
                "currency": "INR",
                "receipt": receipt,
                "notes": notes,
                "payment_capture": 1,
            },
            auth=self._auth,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    async def create_order(
        self, *, amount_rupees: int, receipt: str, notes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a Razorpay order for ``amount_rupees`` (converted to paise)."""
        self._require_enabled()
        try:
            return await asyncio.to_thread(self._sync_create_order, amount_rupees, receipt, notes or {})
        except requests.RequestException as exc:
            logger.error("Razorpay order creation failed", extra={"error": str(exc), "receipt": receipt})
            raise ServiceUnavailableException("Could not create payment order") from exc

    def verify_payment_signature(
        self, *, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str
    ) -> bool:
        """Verify the checkout callback signature (HMAC-SHA256 over order_id|payment_id)."""
        if not self.enabled:
            return False
        payload = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, razorpay_signature)

    def _sync_create_refund(self, payment_id: str, amount_rupees: int, notes: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{API_BASE}/payments/{payment_id}/refund",
            json={"amount": amount_rupees * 100, "notes": notes},
            auth=self._auth,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    async def create_refund(
        self, *, payment_id: str, amount_rupees: int, notes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Refund ``amount_rupees`` of a captured payment (converted to paise)."""
        self._require_enabled()
        try:
            return await asyncio.to_thread(self._sync_create_refund, payment_id, amount_rupees, notes or {})
        except requests.RequestException as exc:
            logger.error("Razorpay refund failed", extra={"error": str(exc), "payment_id": payment_id})
            raise ServiceUnavailableException("Could not process refund") from exc

    def _sync_fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        resp = requests.get(f"{API_BASE}/payments/{payment_id}", auth=self._auth, timeout=15)
        resp.raise_for_status()
        return resp.json()

    async def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        self._require_enabled()
        return await asyncio.to_thread(self._sync_fetch_payment, payment_id)


razorpay_service = RazorpayService()
