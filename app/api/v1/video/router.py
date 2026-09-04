"""Video consultation and therapist slot management API endpoints."""

from __future__ import annotations

import base64
import json
import secrets
import struct
import time
from typing import List, Optional

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.helpers import item_response
from app.config import settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.responses import success_response
from app.dependencies.auth import get_current_user_optional, get_current_active_user
from app.models.booking import Booking
from app.models.therapist_slot import TherapistSlot
from app.models.therapy_booking import TherapyBooking
from app.models.user import User
from app.services.email_service import email_service

router = APIRouter(prefix="/video", tags=["Video Consultation"])


def generate_zego_kit_token(
    app_id: int,
    server_secret: str,
    room_id: str,
    user_id: str,
    user_name: str,
    expire_seconds: int = 3600,
) -> str:
    """Generate secure ZegoCloud KitToken for 1-on-1 Video Consultation."""
    now = int(time.time())
    expire = now + expire_seconds
    nonce = secrets.randbits(31)

    payload_dict = {
        "app_id": app_id,
        "user_id": user_id,
        "nonce": nonce,
        "ctime": now,
        "expire": expire,
        "payload": "",
    }

    # Key is first 16 bytes of server_secret (AES-128)
    key = server_secret.encode("utf-8")[:16]
    iv = secrets.token_bytes(16)

    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(json.dumps(payload_dict).encode("utf-8")) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    expire_bytes = struct.pack(">q", expire)
    iv_len_bytes = struct.pack(">h", len(iv))
    content_len_bytes = struct.pack(">h", len(ciphertext))

    binary_data = b"\x00\x00\x00\x00" + expire_bytes + iv_len_bytes + iv + content_len_bytes + ciphertext
    token04_str = "04" + base64.b64encode(binary_data).decode("utf-8")

    user_data = {
        "userID": user_id,
        "roomID": room_id,
        "userName": user_name,
        "appID": app_id,
    }
    user_data_b64 = base64.b64encode(json.dumps(user_data).encode("utf-8")).decode("utf-8")

    return f"{token04_str}#{user_data_b64}"


class TokenRequest(BaseModel):
    roomId: str
    # userId/userName are ignored — identity always comes from the access token
    # so a caller can't mint a token impersonating somebody else.
    userId: Optional[str] = None
    userName: Optional[str] = None


BOOKING_ROOM_PREFIX = "booking_"

#: Roles allowed to join any consultation room for support purposes.
STAFF_ROLES = {"super_admin", "admin", "support"}


async def _authorize_room(room_id: str, user: User) -> None:
    """Only let a caller into a room they're actually a party to.

    Rooms named ``booking_<reference>`` belong to a therapy booking, so the
    caller must be that booking's patient or its assigned therapist. Admins
    with booking visibility may join for support. Any other room id is a
    private ad-hoc session and is allowed for authenticated users.
    """
    if not room_id.startswith(BOOKING_ROOM_PREFIX):
        return

    reference = room_id[len(BOOKING_ROOM_PREFIX):]
    booking = await TherapyBooking.find_one({"reference": reference})
    if booking is None:
        # Nothing to check against — treat like an ad-hoc room.
        return

    uid = str(user.id)
    if booking.patient_id == uid or booking.assigned_staff_id == uid:
        return

    # Back-office staff may join for support. This is a role check on purpose:
    # every therapist holds `therapy_bookings:view` so they can see their own
    # assignments, so that permission would let any therapist into any call.
    if user.is_superuser or user.role in STAFF_ROLES:
        return

    raise ForbiddenException("You are not a participant of this consultation")


class SlotCreateRequest(BaseModel):
    date: str  # YYYY-MM-DD
    start_time: str  # e.g. "10:00"
    end_time: str  # e.g. "11:00"


@router.get("/generate-token", summary="Generate ZegoCloud video token (GET)")
async def generate_token_get(
    roomId: str = Query(..., description="Video room ID"),
    user: User = Depends(get_current_active_user),
) -> dict:
    """Mint a ZegoCloud KitToken for the signed-in user.

    The identity baked into the token is always the caller's own — it is never
    taken from the request — and access to a booking's room is checked before
    a token is issued.
    """
    if not roomId:
        raise BadRequestException("roomId is required")

    await _authorize_room(roomId, user)

    token = generate_zego_kit_token(
        app_id=settings.ZEGO_APP_ID,
        server_secret=settings.ZEGO_SERVER_SECRET,
        room_id=roomId,
        user_id=str(user.id),
        user_name=user.name or "User",
        expire_seconds=3600,
    )

    return success_response(
        data={
            "token": token,
            "appId": settings.ZEGO_APP_ID,
            "roomId": roomId,
            "userId": str(user.id),
            "userName": user.name,
            "expireTime": 3600,
        },
        message="Video token generated successfully",
    )


@router.post("/generate-token", summary="Generate ZegoCloud video token (POST)")
async def generate_token_post(
    payload: TokenRequest,
    user: User = Depends(get_current_active_user),
) -> dict:
    """Generate a secure ZegoCloud KitToken (POST body version)."""
    return await generate_token_get(roomId=payload.roomId, user=user)


@router.post("/send-meeting-email/{booking_id}", summary="Send video meeting email notification")
async def send_meeting_email(
    booking_id: str,
    background_tasks: BackgroundTasks,
    user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """Send meeting invitation/reminder email to patient & therapist 5 mins before session."""
    booking = await Booking.get(booking_id)
    if not booking:
        raise NotFoundException("Booking not found")

    meeting_url = f"{settings.FRONTEND_URL}/video-consultation?roomId={booking.reference}"
    
    # 1. Send email to patient
    if booking.contact_email:
        background_tasks.add_task(
            email_service.send_video_meeting_reminder,
            to=booking.contact_email,
            name=booking.patient_name,
            service_name=booking.service_name,
            meeting_link=meeting_url,
            date_time=f"{booking.preferred_date} {booking.preferred_time or ''}",
        )

    # 2. Send email to therapist if assigned
    if booking.assigned_staff_id:
        therapist = await User.get(booking.assigned_staff_id)
        if therapist and therapist.email:
            background_tasks.add_task(
                email_service.send_video_meeting_reminder,
                to=therapist.email,
                name=therapist.name,
                service_name=booking.service_name,
                meeting_link=meeting_url,
                date_time=f"{booking.preferred_date} {booking.preferred_time or ''}",
            )

    return success_response(message="Meeting email notifications scheduled successfully")


# ---- Therapist Slot Management ----

@router.get("/therapist-slots", summary="Get therapist slots")
async def get_therapist_slots(
    therapist_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
) -> dict:
    """Fetch available slots for a specific therapist or date."""
    query = {}
    if therapist_id:
        query["therapist_id"] = therapist_id
    if date:
        query["date"] = date

    slots = await TherapistSlot.find(query).sort("+start_time").to_list()
    data = [s.model_dump(mode="json") for s in slots]
    for d in data:
        d["id"] = str(d.pop("_id", d.get("id")))

    return success_response(data=data, message="Therapist slots fetched successfully")


@router.post("/therapist-slots", summary="Create therapist slot")
async def create_therapist_slot(
    payload: SlotCreateRequest,
    user: User = Depends(get_current_active_user),
) -> dict:
    """Therapist creates an available time slot."""
    if user.role != "therapist" and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only therapists can manage time slots",
        )

    # Check if slot already exists
    existing = await TherapistSlot.find_one({
        "therapist_id": str(user.id),
        "date": payload.date,
        "start_time": payload.start_time,
    })
    if existing:
        raise BadRequestException("Slot already exists for this time")

    slot = TherapistSlot(
        therapist_id=str(user.id),
        therapist_name=user.name,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        is_booked=False,
    )
    await slot.insert()
    return item_response(TherapistSlot, slot, "Time slot created successfully")


@router.delete("/therapist-slots/{slot_id}", summary="Delete therapist slot")
async def delete_therapist_slot(
    slot_id: str,
    user: User = Depends(get_current_active_user),
) -> dict:
    """Delete an unbooked slot."""
    slot = await TherapistSlot.get(slot_id)
    if not slot:
        raise NotFoundException("Slot not found")
    if slot.is_booked:
        raise BadRequestException("Cannot delete a booked slot")
    if slot.therapist_id != str(user.id) and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    await slot.delete()
    return success_response(message="Slot deleted successfully")
