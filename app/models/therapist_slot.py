"""Therapist Slot model for managing therapist availability and automatic slot booking."""

from __future__ import annotations

from typing import Optional
import pymongo

from app.models.base import TimestampedDocument
from app.models.enums import SlotType


class TherapistSlot(TimestampedDocument):
    """A bookable time slot published by a therapist.

    Used both for 1-on-1 video consultations and for home visits — the
    ``slot_type`` field separates the two. It defaults to ``video`` because
    the video consultation feature shipped first and its existing rows have
    no ``slot_type`` stored; home-visit slots always set it explicitly.
    """

    therapist_id: str
    therapist_name: str
    slot_type: SlotType = SlotType.VIDEO
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM e.g. "10:00"
    end_time: str  # HH:MM e.g. "11:00"
    is_booked: bool = False
    booked_by_user_id: Optional[str] = None
    booked_by_patient_name: Optional[str] = None
    booking_reference: Optional[str] = None
    #: Set when a TherapyBooking claims this slot, so cancelling can release it.
    therapy_booking_id: Optional[str] = None

    class Settings:
        name = "therapist_slots"
        indexes = [
            [("therapist_id", pymongo.ASCENDING), ("date", pymongo.ASCENDING)],
            [("is_booked", pymongo.ASCENDING)],
            [("date", pymongo.ASCENDING), ("start_time", pymongo.ASCENDING)],
            [("slot_type", pymongo.ASCENDING), ("therapist_id", pymongo.ASCENDING)],
        ]
