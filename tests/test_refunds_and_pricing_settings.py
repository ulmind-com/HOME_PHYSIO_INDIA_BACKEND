"""Refund policy and admin-configurable pricing settings tests."""

import datetime as dt
import hashlib
import hmac

import pytest

from app.models.pricing_settings import PricingSettings
from app.services import therapy_booking_service as tb_module


@pytest.fixture(autouse=True)
def fake_razorpay(monkeypatch):
    async def _fake_create_order(*, amount_rupees, receipt, notes=None):
        return {"id": f"order_fake_{receipt}", "amount": amount_rupees * 100, "currency": "INR"}

    async def _fake_create_refund(*, payment_id, amount_rupees, notes=None):
        return {"id": f"rfnd_fake_{payment_id}", "amount": amount_rupees * 100}

    monkeypatch.setattr(tb_module.razorpay_service, "create_order", _fake_create_order)
    monkeypatch.setattr(tb_module.razorpay_service, "create_refund", _fake_create_refund)
    monkeypatch.setattr(tb_module.razorpay_service, "enabled", True)

    import app.services.razorpay_service as rp_module
    monkeypatch.setattr(rp_module.settings, "RAZORPAY_KEY_SECRET", "dummy_secret")


def _sign(order_id: str, payment_id: str) -> str:
    payload = f"{order_id}|{payment_id}"
    return hmac.new(b"dummy_secret", payload.encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture
def physio_payload():
    return {
        "patient_name": "Test Patient",
        "contact_phone": "9998887776",
        "address": "42 Test Street",
        "service_category": "physiotherapy",
        "preferred_date": "2026-09-10",
        "shift": "morning",
        "time_slot": "09:00 - 09:40",
        "frequency_type": "daily",
        "daily_visits_per_day": 1,
        "equipment": [],
    }


async def _create_and_pay(client, auth_headers, payload):
    create_resp = await client.post("/api/v1/therapy-bookings", headers=auth_headers, json=payload)
    data = create_resp.json()["data"]
    booking_id = data["booking"]["id"]
    order_id = data["razorpay_order_id"]
    signature = _sign(order_id, "pay_fake_1")
    await client.post(
        f"/api/v1/therapy-bookings/{booking_id}/verify-payment",
        headers=auth_headers,
        json={"razorpay_order_id": order_id, "razorpay_payment_id": "pay_fake_1", "razorpay_signature": signature},
    )
    return booking_id, data["booking"]["total_amount"]


async def test_admin_can_change_daily_visit_fee_and_it_affects_new_bookings(client, auth_headers, physio_payload):
    resp = await client.put(
        "/api/v1/settings/pricing", headers=auth_headers, json={"daily_visit_fee_1": 550}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["daily_visit_fee_1"] == 550

    quote_resp = await client.post(
        "/api/v1/therapy-bookings/quote",
        headers=auth_headers,
        json={"service_category": "physiotherapy", "frequency_type": "daily", "daily_visits_per_day": 1, "equipment": []},
    )
    assert quote_resp.status_code == 200
    assert quote_resp.json()["data"]["visit_fee"] == 550


async def test_admin_can_change_commission_percent(client, auth_headers):
    resp = await client.put(
        "/api/v1/settings/pricing", headers=auth_headers, json={"platform_fee_physiotherapy_percent": 25}
    )
    assert resp.status_code == 200

    quote_resp = await client.post(
        "/api/v1/therapy-bookings/quote",
        headers=auth_headers,
        json={"service_category": "physiotherapy", "frequency_type": "daily", "daily_visits_per_day": 1, "equipment": []},
    )
    data = quote_resp.json()["data"]
    assert data["platform_fee_percent"] == 25
    assert data["platform_fee_amount"] == round(data["total_amount"] * 0.25)


async def test_pricing_settings_requires_auth(client):
    resp = await client.get("/api/v1/settings/pricing")
    assert resp.status_code == 401


async def test_cancel_far_in_advance_gets_full_refund(client, auth_headers, physio_payload):
    # Cancellation window default is 24h; the fixture date is far in the future.
    booking_id, total_amount = await _create_and_pay(client, auth_headers, physio_payload)

    resp = await client.post(
        f"/api/v1/therapy-bookings/{booking_id}/cancel", headers=auth_headers, json={"reason": "changed my mind"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "cancelled"
    assert data["payment_status"] == "refunded"
    assert data["refund_amount"] == total_amount


async def test_cancel_within_window_follows_late_refund_policy(client, auth_headers, physio_payload):
    # Book a slot starting in 2 hours from now — inside the default 24h full-refund window.
    near_future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)
    payload = {
        **physio_payload,
        "preferred_date": near_future.date().isoformat(),
        "shift": "morning",
        "time_slot": f"{near_future.hour:02d}:00 - {near_future.hour:02d}:40",
    }
    booking_id, total_amount = await _create_and_pay(client, auth_headers, payload)

    resp = await client.post(
        f"/api/v1/therapy-bookings/{booking_id}/cancel", headers=auth_headers, json={"reason": "last minute"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "cancelled"
    # Default late-cancellation refund percent is 0%, so no refund should be issued.
    assert data["payment_status"] == "paid"
    assert data["refund_amount"] == 0


async def test_admin_rejecting_a_paid_booking_issues_full_refund(client, auth_headers, physio_payload):
    booking_id, total_amount = await _create_and_pay(client, auth_headers, physio_payload)

    resp = await client.patch(
        f"/api/v1/therapy-bookings/{booking_id}/status",
        headers=auth_headers,
        params={"status": "rejected"},
        json={"reason": "no therapist available"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "rejected"
    assert data["payment_status"] == "refunded"
    assert data["refund_amount"] == total_amount


async def test_cannot_cancel_someone_elses_booking(client, auth_headers, physio_payload):
    booking_id, _ = await _create_and_pay(client, auth_headers, physio_payload)

    # A different (unauthenticated-as-owner) actor shouldn't be able to cancel it.
    import app.services.therapy_booking_service as svc_module
    with pytest.raises(Exception):
        await svc_module.therapy_booking_service.patient_cancel(booking_id, "someone-else-id", "not mine")
