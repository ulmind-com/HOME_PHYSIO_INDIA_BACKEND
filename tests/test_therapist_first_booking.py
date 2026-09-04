"""Therapist-first booking flow: slots, equipment, gender matching."""

import datetime as dt

import pytest

from app.models.enums import EquipmentOwner, ServiceCategory, SlotType
from app.models.therapist_slot import TherapistSlot
from app.models.therapy_equipment import TherapyEquipment
from app.models.user import User
from app.core.security import hash_password
from app.services import therapy_booking_service as tb_module


@pytest.fixture(autouse=True)
def fake_razorpay(monkeypatch):
    async def _fake_create_order(*, amount_rupees, receipt, notes=None):
        return {"id": f"order_fake_{receipt}", "amount": amount_rupees * 100, "currency": "INR"}

    monkeypatch.setattr(tb_module.razorpay_service, "create_order", _fake_create_order)
    monkeypatch.setattr(tb_module.razorpay_service, "enabled", True)


async def _make_therapist(name: str, user_type: str, gender: str) -> User:
    user = User(
        name=name,
        email=f"{name.lower().replace(' ', '.')}@test.com",
        hashed_password=hash_password("Test@12345"),
        role="therapist",
        user_type=user_type,
        gender=gender,
        verification_status="approved",
        is_active=True,
        is_email_verified=True,
    )
    await user.insert()
    return user


async def _make_slot(therapist: User, date: str, start: str, end: str) -> TherapistSlot:
    slot = TherapistSlot(
        therapist_id=str(therapist.id),
        therapist_name=therapist.name,
        slot_type=SlotType.HOME_VISIT,
        date=date,
        start_time=start,
        end_time=end,
    )
    await slot.insert()
    return slot


async def _make_equipment(category: ServiceCategory, name: str, charge: int, therapist=None):
    item = TherapyEquipment(
        name=name,
        slug=name.lower().replace(" ", "-"),
        category=category,
        charge=charge,
        owner_type=EquipmentOwner.THERAPIST if therapist else EquipmentOwner.PLATFORM,
        therapist_id=str(therapist.id) if therapist else None,
        therapist_name=therapist.name if therapist else None,
    )
    await item.insert()
    return item


def _future_date(days: int = 7) -> str:
    return (dt.date.today() + dt.timedelta(days=days)).isoformat()


def _massage_payload(therapist, slot, equipment_ids=None):
    return {
        "patient_name": "Test Patient",
        "patient_gender": "male",
        "contact_phone": "9998887776",
        "address": "42 Test Street",
        "service_category": "massage_therapy",
        "massage_type": "normal_oil",
        "massage_duration_minutes": 50,
        "therapist_id": str(therapist.id),
        "slot_id": str(slot.id),
        "equipment_ids": equipment_ids or [],
    }


async def test_booking_a_slot_marks_it_taken(client, auth_headers, db):
    therapist = await _make_therapist("Male Masseur", "massage_therapist", "male")
    slot = await _make_slot(therapist, _future_date(), "10:00", "11:00")

    resp = await client.post(
        "/api/v1/therapy-bookings", headers=auth_headers, json=_massage_payload(therapist, slot)
    )
    assert resp.status_code == 201, resp.text
    booking = resp.json()["data"]["booking"]

    assert booking["assigned_staff_id"] == str(therapist.id)
    assert booking["slot_id"] == str(slot.id)
    # Slot details flow onto the booking
    assert booking["time_slot"] == "10:00 - 11:00"
    assert booking["shift"] == "morning"

    refreshed = await TherapistSlot.get(str(slot.id))
    assert refreshed.is_booked is True
    assert refreshed.therapy_booking_id == booking["id"]


async def test_same_slot_cannot_be_booked_twice(client, auth_headers, db):
    therapist = await _make_therapist("Solo Masseur", "massage_therapist", "male")
    slot = await _make_slot(therapist, _future_date(), "12:00", "13:00")

    first = await client.post(
        "/api/v1/therapy-bookings", headers=auth_headers, json=_massage_payload(therapist, slot)
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/therapy-bookings", headers=auth_headers, json=_massage_payload(therapist, slot)
    )
    assert second.status_code == 400
    assert "just booked" in second.json()["message"].lower()


async def test_availability_hides_booked_slots(client, auth_headers, db):
    therapist = await _make_therapist("Busy Masseur", "massage_therapist", "male")
    free = await _make_slot(therapist, _future_date(), "09:00", "10:00")
    taken = await _make_slot(therapist, _future_date(), "15:00", "16:00")

    await client.post(
        "/api/v1/therapy-bookings", headers=auth_headers, json=_massage_payload(therapist, taken)
    )

    resp = await client.get(
        "/api/v1/therapy-bookings/therapist-availability",
        headers=auth_headers,
        params={"therapist_id": str(therapist.id)},
    )
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["data"]]
    assert str(free.id) in ids
    assert str(taken.id) not in ids


async def test_massage_equipment_is_priced_into_the_booking(client, auth_headers, db):
    therapist = await _make_therapist("Equipped Masseur", "massage_therapist", "male")
    slot = await _make_slot(therapist, _future_date(), "10:00", "11:00")
    table = await _make_equipment(ServiceCategory.MASSAGE_THERAPY, "Massage Table X", 200)
    own_gun = await _make_equipment(ServiceCategory.MASSAGE_THERAPY, "My Massage Gun", 150, therapist=therapist)

    resp = await client.post(
        "/api/v1/therapy-bookings",
        headers=auth_headers,
        json=_massage_payload(therapist, slot, [str(table.id), str(own_gun.id)]),
    )
    assert resp.status_code == 201, resp.text
    booking = resp.json()["data"]["booking"]

    # Normal oil massage 800 + 200 table + 150 gun
    assert booking["visit_fee"] == 800
    assert booking["machine_charge"] == 350
    assert booking["total_amount"] == 1150
    assert {e["name"] for e in booking["equipment_items"]} == {"Massage Table X", "My Massage Gun"}


async def test_cannot_book_another_therapists_personal_equipment(client, auth_headers, db):
    therapist = await _make_therapist("Booking Masseur", "massage_therapist", "male")
    other = await _make_therapist("Other Masseur", "massage_therapist", "male")
    slot = await _make_slot(therapist, _future_date(), "10:00", "11:00")
    foreign = await _make_equipment(ServiceCategory.MASSAGE_THERAPY, "Their Own Kit", 500, therapist=other)

    resp = await client.post(
        "/api/v1/therapy-bookings",
        headers=auth_headers,
        json=_massage_payload(therapist, slot, [str(foreign.id)]),
    )
    assert resp.status_code == 400
    assert "different therapist" in resp.json()["message"].lower()


async def test_wrong_category_equipment_is_rejected(client, auth_headers, db):
    therapist = await _make_therapist("Category Masseur", "massage_therapist", "male")
    slot = await _make_slot(therapist, _future_date(), "10:00", "11:00")
    yoga_mat = await _make_equipment(ServiceCategory.YOGA_THERAPY, "Yoga Mat Pro", 50)

    resp = await client.post(
        "/api/v1/therapy-bookings",
        headers=auth_headers,
        json=_massage_payload(therapist, slot, [str(yoga_mat.id)]),
    )
    assert resp.status_code == 400
    assert "not available for" in resp.json()["message"].lower()


async def test_massage_gender_mismatch_is_blocked(client, auth_headers, db):
    female_therapist = await _make_therapist("Female Masseur", "massage_therapist", "female")
    slot = await _make_slot(female_therapist, _future_date(), "10:00", "11:00")

    payload = _massage_payload(female_therapist, slot)
    payload["patient_gender"] = "male"

    resp = await client.post("/api/v1/therapy-bookings", headers=auth_headers, json=payload)
    assert resp.status_code == 400
    assert "same gender" in resp.json()["message"].lower()

    # And the slot must remain free after the rejected attempt
    refreshed = await TherapistSlot.get(str(slot.id))
    assert refreshed.is_booked is False


async def test_wrong_therapist_type_is_blocked(client, auth_headers, db):
    yogi = await _make_therapist("Yoga Person", "yoga_therapist", "male")
    slot = await _make_slot(yogi, _future_date(), "10:00", "11:00")

    resp = await client.post(
        "/api/v1/therapy-bookings", headers=auth_headers, json=_massage_payload(yogi, slot)
    )
    assert resp.status_code == 400
    assert "does not provide" in resp.json()["message"].lower()


async def test_cancelling_frees_the_slot(client, auth_headers, db):
    therapist = await _make_therapist("Cancel Masseur", "massage_therapist", "male")
    slot = await _make_slot(therapist, _future_date(), "10:00", "11:00")

    created = await client.post(
        "/api/v1/therapy-bookings", headers=auth_headers, json=_massage_payload(therapist, slot)
    )
    booking_id = created.json()["data"]["booking"]["id"]

    cancel = await client.post(
        f"/api/v1/therapy-bookings/{booking_id}/cancel",
        headers=auth_headers,
        json={"reason": "changed my mind"},
    )
    assert cancel.status_code == 200, cancel.text

    refreshed = await TherapistSlot.get(str(slot.id))
    assert refreshed.is_booked is False
    assert refreshed.therapy_booking_id is None


async def test_equipment_for_booking_merges_platform_and_therapist_items(client, auth_headers, db):
    therapist = await _make_therapist("Catalogue Masseur", "massage_therapist", "male")
    other = await _make_therapist("Unrelated Masseur", "massage_therapist", "male")
    platform_item = await _make_equipment(ServiceCategory.MASSAGE_THERAPY, "Platform Stones", 250)
    own_item = await _make_equipment(ServiceCategory.MASSAGE_THERAPY, "Personal Oils", 120, therapist=therapist)
    others_item = await _make_equipment(ServiceCategory.MASSAGE_THERAPY, "Someone Elses", 999, therapist=other)
    yoga_item = await _make_equipment(ServiceCategory.YOGA_THERAPY, "Yoga Strap Pro", 50)

    resp = await client.get(
        "/api/v1/therapy-equipment/for-booking",
        headers=auth_headers,
        params={"category": "massage_therapy", "therapist_id": str(therapist.id)},
    )
    assert resp.status_code == 200
    names = {e["name"] for e in resp.json()["data"]}

    assert platform_item.name in names          # platform equipment for this category
    assert own_item.name in names               # this therapist's own equipment
    assert others_item.name not in names        # never another therapist's
    assert yoga_item.name not in names          # never another category


# ── Regression tests for the security / correctness fixes ──────────────


async def test_video_token_requires_authentication(client):
    """Anyone could previously mint a Zego token for any room."""
    resp = await client.get("/api/v1/video/generate-token", params={"roomId": "booking_ANY"})
    assert resp.status_code == 401


async def test_video_token_rejects_a_room_you_are_not_part_of(client, auth_headers, db):
    therapist = await _make_therapist("Room Masseur", "massage_therapist", "male")
    slot = await _make_slot(therapist, _future_date(), "10:00", "11:00")
    created = await client.post(
        "/api/v1/therapy-bookings", headers=auth_headers, json=_massage_payload(therapist, slot)
    )
    reference = created.json()["data"]["booking"]["reference"]

    # A therapist who has nothing to do with this booking
    outsider = await _make_therapist("Nosy Outsider", "massage_therapist", "male")
    login = await client.post(
        "/api/v1/auth/login", json={"email": outsider.email, "password": "Test@12345"}
    )
    outsider_headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    resp = await client.get(
        "/api/v1/video/generate-token",
        headers=outsider_headers,
        params={"roomId": f"booking_{reference}"},
    )
    assert resp.status_code == 403


async def test_directory_does_not_leak_therapist_contact_details(client, auth_headers, db):
    await _make_therapist("Private Physio", "physiotherapist", "male")

    resp = await client.get(
        "/api/v1/therapists", headers=auth_headers, params={"user_type": "physiotherapist"}
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert items, "expected at least one therapist"

    leaked = {"email", "phone", "address", "pincode", "documents", "extra_permissions", "is_superuser"}
    for field in leaked:
        assert field not in items[0], f"{field} must not be exposed to patients"
    assert items[0]["name"]


async def test_reassignment_frees_the_previous_therapists_slot(client, auth_headers, db):
    first = await _make_therapist("First Masseur", "massage_therapist", "male")
    second = await _make_therapist("Second Masseur", "massage_therapist", "male")
    old_slot = await _make_slot(first, _future_date(), "10:00", "11:00")
    new_slot = await _make_slot(second, _future_date(), "14:00", "15:00")

    created = await client.post(
        "/api/v1/therapy-bookings", headers=auth_headers, json=_massage_payload(first, old_slot)
    )
    booking_id = created.json()["data"]["booking"]["id"]

    # Pay + approve so the booking becomes assignable
    booking = await tb_module.TherapyBooking.get(booking_id)
    booking.payment_status = "paid"
    booking.status = "approved"
    await booking.save()

    resp = await client.post(
        f"/api/v1/therapy-bookings/{booking_id}/assign",
        headers=auth_headers,
        json={
            "assigned_staff_id": str(second.id),
            "assigned_staff_name": second.name,
            "slot_id": str(new_slot.id),
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["assigned_staff_id"] == str(second.id)
    assert data["time_slot"] == "14:00 - 15:00"

    assert (await TherapistSlot.get(str(old_slot.id))).is_booked is False   # handed back
    assert (await TherapistSlot.get(str(new_slot.id))).is_booked is True    # taken


async def test_cannot_book_a_slot_in_the_past(client, auth_headers, db):
    therapist = await _make_therapist("Past Masseur", "massage_therapist", "male")
    past = await _make_slot(
        therapist, (dt.date.today() - dt.timedelta(days=3)).isoformat(), "10:00", "11:00"
    )

    resp = await client.post(
        "/api/v1/therapy-bookings", headers=auth_headers, json=_massage_payload(therapist, past)
    )
    assert resp.status_code == 400
    assert "past" in resp.json()["message"].lower()


async def test_therapist_cannot_complete_their_own_visit(client, auth_headers, db):
    therapist = await _make_therapist("Eager Masseur", "massage_therapist", "male")
    slot = await _make_slot(therapist, _future_date(), "10:00", "11:00")
    created = await client.post(
        "/api/v1/therapy-bookings", headers=auth_headers, json=_massage_payload(therapist, slot)
    )
    booking_id = created.json()["data"]["booking"]["id"]

    login = await client.post(
        "/api/v1/auth/login", json={"email": therapist.email, "password": "Test@12345"}
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    resp = await client.patch(
        f"/api/v1/therapy-bookings/{booking_id}/my-status",
        headers=headers,
        params={"status": "completed"},
        json={},
    )
    assert resp.status_code == 403
    assert "admin" in resp.json()["message"].lower()


async def test_abandoned_unpaid_booking_releases_its_slot(client, auth_headers, db):
    therapist = await _make_therapist("Ghost Masseur", "massage_therapist", "male")
    slot = await _make_slot(therapist, _future_date(), "10:00", "11:00")
    created = await client.post(
        "/api/v1/therapy-bookings", headers=auth_headers, json=_massage_payload(therapist, slot)
    )
    booking_id = created.json()["data"]["booking"]["id"]
    assert (await TherapistSlot.get(str(slot.id))).is_booked is True

    # Age the unpaid booking past the hold window
    booking = await tb_module.TherapyBooking.get(booking_id)
    booking.created_at = tb_module.utcnow() - dt.timedelta(hours=2)
    await booking.save()

    released = await tb_module.therapy_booking_service.release_abandoned_slots()
    assert released == 1

    assert (await TherapistSlot.get(str(slot.id))).is_booked is False
    assert (await tb_module.TherapyBooking.get(booking_id)).status == "cancelled"
