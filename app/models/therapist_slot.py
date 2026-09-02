"""Therapist Slot model for managing therapist availability and automatic slot booking."""

from __future__ import annotations

from typing import Optional
import pymongo

from app.models.base import TimestampedDocument


class TherapistSlot(TimestampedDocument):
    """Available time slots managed by therapists for 1-on-1 consultations."""

    therapist_id: str
    therapist_name: str
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM e.g. "10:00"
    end_time: str  # HH:MM e.g. "11:00"
    is_booked: bool = False
    booked_by_user_id: Optional[str] = None
    booked_by_patient_name: Optional[str] = None
    booking_reference: Optional[str] = None

    class Settings:
        name = "therapist_slots"
        indexes = [
            [("therapist_id", pymongo.ASCENDING), ("date", pymongo.ASCENDING)],
            [("is_booked", pymongo.ASCENDING)],
            [("date", pymongo.ASCENDING), ("start_time", pymongo.ASCENDING)],
        ]
