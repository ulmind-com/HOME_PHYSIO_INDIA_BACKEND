"""Razorpay signature verification tests (pure HMAC logic, no network)."""

import hashlib
import hmac

from app.config import settings
from app.services.razorpay_service import RazorpayService


def _sign(order_id: str, payment_id: str, secret: str) -> str:
    payload = f"{order_id}|{payment_id}"
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def test_valid_signature_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_dummy")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "dummy_secret")
    service = RazorpayService()

    signature = _sign("order_ABC123", "pay_XYZ789", "dummy_secret")

    assert service.verify_payment_signature(
        razorpay_order_id="order_ABC123",
        razorpay_payment_id="pay_XYZ789",
        razorpay_signature=signature,
    ) is True


def test_tampered_signature_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_dummy")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "dummy_secret")
    service = RazorpayService()

    signature = _sign("order_ABC123", "pay_XYZ789", "dummy_secret")

    assert service.verify_payment_signature(
        razorpay_order_id="order_ABC123",
        razorpay_payment_id="pay_DIFFERENT",  # payment id swapped after signing
        razorpay_signature=signature,
    ) is False


def test_wrong_secret_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_dummy")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "dummy_secret")
    service = RazorpayService()

    signature = _sign("order_ABC123", "pay_XYZ789", "wrong_secret")

    assert service.verify_payment_signature(
        razorpay_order_id="order_ABC123",
        razorpay_payment_id="pay_XYZ789",
        razorpay_signature=signature,
    ) is False


def test_disabled_service_rejects_everything(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "")
    service = RazorpayService()

    assert service.verify_payment_signature(
        razorpay_order_id="order_ABC123",
        razorpay_payment_id="pay_XYZ789",
        razorpay_signature="anything",
    ) is False
