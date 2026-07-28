"""Booking public-create and admin-workflow tests."""

import pytest


@pytest.fixture
def booking_payload():
    return {
        "patient_name": "Test Patient",
        "contact_phone": "9998887776",
        "service_name": "Home Nursing",
        "preferred_date": "2026-09-01",
        "address": "42 Test Street",
    }


async def test_public_create_booking(client, booking_payload):
    resp = await client.post("/api/v1/bookings", json=booking_payload)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["reference"].startswith("NHB-")
    assert data["status"] == "pending"


async def test_list_bookings_requires_auth(client):
    resp = await client.get("/api/v1/bookings")
    assert resp.status_code == 401


async def test_approve_and_reject_flow(client, auth_headers, booking_payload):
    created = await client.post("/api/v1/bookings", json=booking_payload)
    booking_id = created.json()["data"]["id"]

    approved = await client.post(
        f"/api/v1/bookings/{booking_id}/approve", headers=auth_headers
    )
    assert approved.json()["data"]["status"] == "approved"

    # Approved is not terminal, cancelling is allowed.
    cancelled = await client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers=auth_headers,
        json={"reason": "duplicate"},
    )
    assert cancelled.json()["data"]["status"] == "cancelled"

    # Cancelled is terminal — approving again should fail.
    again = await client.post(
        f"/api/v1/bookings/{booking_id}/approve", headers=auth_headers
    )
    assert again.status_code == 400


async def test_booking_validation_error(client):
    resp = await client.post("/api/v1/bookings", json={"patient_name": "x"})
    assert resp.status_code == 422
    assert resp.json()["success"] is False
    assert isinstance(resp.json()["errors"], list)
