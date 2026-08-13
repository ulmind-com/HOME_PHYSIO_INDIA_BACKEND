"""Booking and patient documents."""

from __future__ import annotations

import datetime as dt
from typing import Optional

import pymongo
from beanie import Indexed
from pydantic import EmailStr, Field

from app.models.base import TimestampedDocument
from app.models.enums import BookingStatus, Gender


class Patient(TimestampedDocument):
    """A patient linked to one or more bookings."""

    name: str
    age: Optional[int] = None
    gender: Optional[Gender] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    medical_notes: Optional[str] = None

    class Settings:
        name = "patients"
        indexes = [[("phone", pymongo.ASCENDING)], [("name", pymongo.TEXT)]]


class Booking(TimestampedDocument):
    """A service booking submitted from the public website."""

    # Human-friendly reference, e.g. "NHH-20260728-AB12".
    reference: Indexed(str, unique=True)  # type: ignore[valid-type]

    # Patient information (denormalised for fast listing + optional link).
    patient_id: Optional[str] = None
    patient_name: str
    patient_age: Optional[int] = None
    patient_gender: Optional[Gender] = None

    # Contact.
    contact_phone: str
    contact_email: Optional[EmailStr] = None

    # Service.
    service_id: Optional[str] = None
    service_name: str

    # Scheduling.
    preferred_date: dt.date
    preferred_time: Optional[str] = None

    # Location.
    address: str
    city: Optional[str] = None
    pincode: Optional[str] = None

    # Emergency contact.
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    # Workflow.
    status: BookingStatus = BookingStatus.PENDING
    assigned_staff_id: Optional[str] = None
    assigned_staff_name: Optional[str] = None
    admin_notes: Optional[str] = None
    message: Optional[str] = None
    source: Optional[str] = None

    class Settings:
        name = "bookings"
        indexes = [
            [("reference", pymongo.ASCENDING)],
            [("status", pymongo.ASCENDING)],
            [("preferred_date", pymongo.DESCENDING)],
            [("service_id", pymongo.ASCENDING)],
            [("created_at", pymongo.DESCENDING)],
            [("patient_name", pymongo.TEXT), ("contact_phone", pymongo.TEXT)],
        ]
