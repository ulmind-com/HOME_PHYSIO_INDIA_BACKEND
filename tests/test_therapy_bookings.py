"""Therapy booking creation + Razorpay payment flow integration tests."""

import hashlib
import hmac

import pytest

from app.services import therapy_booking_service as tb_module


@pytest.fixture(autouse=True)
def fake_razorpay(monkeypatch):
    """Stub the network call to Razorpay so tests never hit the real API."""

    async def _fake_create_order(*, amount_rupees, receipt, notes=None):
        return {"id": f"order_fake_{receipt}", "amount": amount_rupees * 100, "currency": "INR"}

    monkeypatch.setattr(tb_module.razorpay_service, "create_order", _fake_create_order)
    monkeypatch.setattr(tb_module.razorpay_service, "enabled", True)
    monkeypatch.setattr(
        tb_module.razorpay_service,
        "_auth",
        ("rzp_test_dummy", "dummy_secret"),
        raising=False,
    )
    # Route signature verification through the same dummy secret.
    import app.services.razorpay_service as rp_module

    monkeypatch.setattr(rp_module.settings, "RAZORPAY_KEY_SECRET", "dummy_secret")


def _sign(order_id: str, payment_id: str) -> str:
    payload = f"{order_id}|{payment_id}"
    return hmac.new(b"dummy_secret", payload.encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture
def physio_payload():
    return {
        "patient_name": "Test Patient",
        "patient_age": 45,
        "contact_phone": "9998887776",
        "address": "42 Test Street",
        "service_category": "physiotherapy",
        "preferred_date": "2026-09-10",
        "shift": "morning",
        "time_slot": "09:00 - 09:40",
        "frequency_type": "daily",
        "daily_visits_per_day": 1,
        "equipment": ["ift"],
    }


async def test_create_booking_computes_price_and_returns_order(client, auth_headers, physio_payload):
    resp = await client.post("/api/v1/therapy-bookings", headers=auth_headers, json=physio_payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    booking = data["booking"]
    assert booking["visit_fee"] == 400
    assert booking["machine_charge"] == 100
    assert booking["total_amount"] == 500
    assert booking["platform_fee_amount"] == 100
    assert booking["therapist_payout"] == 400
    assert booking["payment_status"] == "pending"
    assert data["razorpay_order_id"].startswith("order_fake_")
    assert data["amount"] == 500 * 100


async def test_massage_booking_requires_gender(client, auth_headers):
    payload = {
        "patient_name": "Test Patient",
        "contact_phone": "9998887776",
        "address": "42 Test Street",
        "service_category": "massage_therapy",
        "preferred_date": "2026-09-10",
        "shift": "evening",
        "time_slot": "18:00 - 18:40",
        "massage_type": "deep_tissue",
        "massage_duration_minutes": 75,
    }
    resp = await client.post("/api/v1/therapy-bookings", headers=auth_headers, json=payload)
    assert resp.status_code == 422


async def test_verify_payment_confirms_booking(client, auth_headers, physio_payload):
    create_resp = await client.post("/api/v1/therapy-bookings", headers=auth_headers, json=physio_payload)
    data = create_resp.json()["data"]
    booking_id = data["booking"]["id"]
    order_id = data["razorpay_order_id"]

    signature = _sign(order_id, "pay_fake_123")
    verify_resp = await client.post(
        f"/api/v1/therapy-bookings/{booking_id}/verify-payment",
        headers=auth_headers,
        json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_fake_123",
            "razorpay_signature": signature,
        },
    )
    assert verify_resp.status_code == 200, verify_resp.text
    confirmed = verify_resp.json()["data"]
    assert confirmed["payment_status"] == "paid"
    assert confirmed["amount_paid"] == 500


async def test_verify_payment_rejects_bad_signature(client, auth_headers, physio_payload):
    create_resp = await client.post("/api/v1/therapy-bookings", headers=auth_headers, json=physio_payload)
    data = create_resp.json()["data"]
    booking_id = data["booking"]["id"]
    order_id = data["razorpay_order_id"]

    verify_resp = await client.post(
        f"/api/v1/therapy-bookings/{booking_id}/verify-payment",
        headers=auth_headers,
        json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_fake_123",
            "razorpay_signature": "not-a-real-signature",
        },
    )
    assert verify_resp.status_code == 400


async def test_cannot_approve_unpaid_booking(client, auth_headers, physio_payload):
    create_resp = await client.post("/api/v1/therapy-bookings", headers=auth_headers, json=physio_payload)
    booking_id = create_resp.json()["data"]["booking"]["id"]

    resp = await client.patch(
        f"/api/v1/therapy-bookings/{booking_id}/status",
        headers=auth_headers,
        params={"status": "approved"},
        json={},
    )
    assert resp.status_code == 400
