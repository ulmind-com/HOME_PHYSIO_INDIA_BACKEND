"""Booking schemas."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import BookingStatus, Gender
from app.schemas.common import IdTimestampSchema


class BookingCreate(BaseModel):
    """Public booking submission payload."""

    patient_name: str = Field(..., min_length=2, max_length=120)
    patient_age: Optional[int] = Field(None, ge=0, le=130)
    patient_gender: Optional[Gender] = None

    contact_phone: str = Field(..., min_length=6, max_length=20)
    contact_email: Optional[EmailStr] = None

    service_id: Optional[str] = None
    service_name: str = Field(..., min_length=2, max_length=200)

    preferred_date: dt.date
    preferred_time: Optional[str] = None

    address: str = Field(..., min_length=3)
    city: Optional[str] = None
    pincode: Optional[str] = None

    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    message: Optional[str] = None


class BookingUpdate(BaseModel):
    """Admin update payload."""

    patient_name: Optional[str] = None
    patient_age: Optional[int] = Field(None, ge=0, le=130)
    patient_gender: Optional[Gender] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    service_name: Optional[str] = None
    preferred_date: Optional[dt.date] = None
    preferred_time: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    admin_notes: Optional[str] = None


class BookingStatusUpdate(BaseModel):
    """Payload for status transitions (reject/cancel with a reason)."""

    reason: Optional[str] = None


class BookingAssign(BaseModel):
    """Assign a staff member to a booking."""

    assigned_staff_id: str
    assigned_staff_name: str


class BookingResponse(IdTimestampSchema):
    reference: str
    patient_id: Optional[str] = None
    patient_name: str
    patient_age: Optional[int] = None
    patient_gender: Optional[Gender] = None
    contact_phone: str
    contact_email: Optional[EmailStr] = None
    service_id: Optional[str] = None
    service_name: str
    preferred_date: dt.date
    preferred_time: Optional[str] = None
    address: str
    city: Optional[str] = None
    pincode: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    status: BookingStatus
    assigned_staff_id: Optional[str] = None
    assigned_staff_name: Optional[str] = None
    admin_notes: Optional[str] = None
    message: Optional[str] = None
