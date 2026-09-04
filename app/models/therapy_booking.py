"""Priced home-visit therapy booking (Physiotherapy / Yoga / Massage / Rehab).

Kept separate from the generic CMS-driven :class:`app.models.booking.Booking`
(used for lead-gen services like elder care, ICU setup, equipment rental)
because this flow has its own structured pricing engine, equipment charges,
package/frequency rules and Razorpay payment lifecycle that don't apply to
the generic booking form.
"""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

import pymongo
from beanie import Indexed
from pydantic import EmailStr, Field

from app.models.base import TimestampedDocument
from app.models.therapy_equipment import BookedEquipment
from app.models.enums import (
    BookingStatus,
    EquipmentCode,
    FrequencyType,
    Gender,
    MassageType,
    PackageDuration,
    PaymentStatus,
    Shift,
    ServiceCategory,
)


class TherapyBooking(TimestampedDocument):
    """A priced, payment-backed home-visit therapy booking."""

    reference: Indexed(str, unique=True)  # type: ignore[valid-type]

    # Patient
    patient_id: Optional[str] = None
    patient_name: str
    patient_age: Optional[int] = None
    patient_gender: Optional[Gender] = None
    contact_phone: str
    contact_email: Optional[EmailStr] = None

    # Location
    address: str
    city: Optional[str] = None
    pincode: Optional[str] = None

    # Service
    service_category: ServiceCategory
    condition_notes: Optional[str] = None

    # Scheduling
    preferred_date: dt.date
    shift: Shift
    time_slot: str
    session_duration_minutes: int = 45

    # Frequency (physiotherapy / yoga_therapy / home_rehabilitation only)
    frequency_type: Optional[FrequencyType] = None
    daily_visits_per_day: Optional[int] = None
    weekly_days_count: Optional[int] = None
    package_duration: Optional[PackageDuration] = None
    package_custom_months: Optional[int] = None

    # Equipment. ``equipment`` holds the legacy hardcoded modality codes and is
    # only populated for bookings made before the equipment catalogue moved into
    # the database; new bookings use ``equipment_items`` (priced snapshots).
    equipment: List[EquipmentCode] = Field(default_factory=list)
    equipment_items: List[BookedEquipment] = Field(default_factory=list)

    # Slot booked from the therapist's own calendar (therapist-first flow).
    slot_id: Optional[str] = None

    # Massage-specific
    massage_type: Optional[MassageType] = None
    massage_duration_minutes: Optional[int] = None

    # Pricing (computed server-side at creation time; never trust client input)
    visit_fee: int = 0
    machine_charge: int = 0
    total_amount: int = 0
    platform_fee_percent: int = 0
    platform_fee_amount: int = 0
    therapist_payout: int = 0

    # Payment (Razorpay)
    payment_status: PaymentStatus = PaymentStatus.PENDING
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    amount_paid: int = 0

    # Cancellation & refund
    cancellation_reason: Optional[str] = None
    cancelled_by: Optional[str] = None  # "patient" | "admin"
    refund_amount: int = 0
    razorpay_refund_id: Optional[str] = None
    refunded_at: Optional[dt.datetime] = None

    # Workflow
    status: BookingStatus = BookingStatus.PENDING
    assigned_staff_id: Optional[str] = None
    assigned_staff_name: Optional[str] = None
    admin_notes: Optional[str] = None

    class Settings:
        name = "therapy_bookings"
        indexes = [
            [("reference", pymongo.ASCENDING)],
            [("status", pymongo.ASCENDING)],
            [("payment_status", pymongo.ASCENDING)],
            [("service_category", pymongo.ASCENDING)],
            [("patient_id", pymongo.ASCENDING)],
            [("assigned_staff_id", pymongo.ASCENDING)],
            [("created_at", pymongo.DESCENDING)],
        ]
