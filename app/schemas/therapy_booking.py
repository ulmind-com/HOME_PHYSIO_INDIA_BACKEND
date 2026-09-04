"""Therapy booking schemas (pricing, creation, payment, admin workflow)."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

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
from app.models.therapy_equipment import BookedEquipment
from app.schemas.common import IdTimestampSchema


class TherapyBookingCreate(BaseModel):
    """Public booking submission — pricing is always computed server-side."""

    patient_name: str = Field(..., min_length=2, max_length=120, pattern=r"^[^<>]+$")
    patient_age: Optional[int] = Field(None, ge=0, le=130)
    patient_gender: Optional[Gender] = None

    contact_phone: str = Field(..., min_length=6, max_length=20, pattern=r"^\+?[0-9\-\s\(\)]+$")
    contact_email: Optional[EmailStr] = None

    address: str = Field(..., min_length=3)
    city: Optional[str] = None
    pincode: Optional[str] = None

    service_category: ServiceCategory
    condition_notes: Optional[str] = Field(None, max_length=2000)

    # Therapist-first flow: pick a therapist and one of their published slots.
    # When ``slot_id`` is given, the date / shift / time_slot below are derived
    # from the slot and may be omitted.
    therapist_id: Optional[str] = None
    slot_id: Optional[str] = None

    preferred_date: Optional[dt.date] = None
    shift: Optional[Shift] = None
    time_slot: Optional[str] = Field(None, min_length=3, max_length=40)
    session_duration_minutes: int = Field(45, ge=40, le=60)

    #: Equipment chosen from the catalogue (platform + that therapist's own).
    equipment_ids: List[str] = Field(default_factory=list)

    # Physiotherapy / Yoga Therapy / Home Rehabilitation
    frequency_type: Optional[FrequencyType] = None
    daily_visits_per_day: Optional[int] = Field(None, ge=1, le=3)
    weekly_days_count: Optional[int] = Field(None, ge=1, le=7)
    package_duration: Optional[PackageDuration] = None
    package_custom_months: Optional[int] = Field(None, ge=1, le=24)
    equipment: List[EquipmentCode] = Field(default_factory=list)

    # Massage Therapy
    massage_type: Optional[MassageType] = None
    massage_duration_minutes: Optional[int] = Field(None, ge=30, le=120)

    @model_validator(mode="after")
    def _validate_by_category(self) -> "TherapyBookingCreate":
        if self.service_category == ServiceCategory.MASSAGE_THERAPY:
            if not self.massage_type:
                raise ValueError("massage_type is required for massage therapy bookings")
            if not self.massage_duration_minutes:
                raise ValueError("massage_duration_minutes is required for massage therapy bookings")
            if not self.patient_gender:
                raise ValueError("patient_gender is required for massage therapy bookings (therapist gender matching)")
            if self.frequency_type:
                raise ValueError("Massage therapy is a single session — it has no frequency or package option")
        else:
            if not self.frequency_type:
                raise ValueError("frequency_type is required")
            if self.frequency_type == FrequencyType.DAILY and not self.daily_visits_per_day:
                raise ValueError("daily_visits_per_day is required for daily frequency")
            if self.frequency_type == FrequencyType.WEEKLY and not self.weekly_days_count:
                raise ValueError("weekly_days_count is required for weekly frequency")
            if self.frequency_type == FrequencyType.PACKAGE:
                if not self.package_duration:
                    raise ValueError("package_duration is required for package frequency")
                if self.package_duration == PackageDuration.CUSTOM and not self.package_custom_months:
                    raise ValueError("package_custom_months is required for a custom package")
            if self.massage_type or self.massage_duration_minutes:
                raise ValueError("massage_type/massage_duration_minutes only apply to massage therapy")

        # Scheduling: either book a therapist's published slot, or supply the
        # date/shift/time_slot explicitly (legacy service-first flow).
        if self.slot_id:
            if not self.therapist_id:
                raise ValueError("therapist_id is required when booking a slot")
        elif not (self.preferred_date and self.shift and self.time_slot):
            raise ValueError(
                "Provide either slot_id (with therapist_id), or preferred_date + shift + time_slot"
            )
        return self


class PricingQuoteRequest(BaseModel):
    """Just the pricing-relevant fields, for a live price-preview widget."""

    service_category: ServiceCategory
    frequency_type: Optional[FrequencyType] = None
    daily_visits_per_day: Optional[int] = Field(None, ge=1, le=3)
    equipment: List[EquipmentCode] = Field(default_factory=list)
    equipment_ids: List[str] = Field(default_factory=list)
    massage_type: Optional[MassageType] = None
    massage_duration_minutes: Optional[int] = Field(None, ge=30, le=120)

    @model_validator(mode="after")
    def _validate_by_category(self) -> "PricingQuoteRequest":
        if self.service_category == ServiceCategory.MASSAGE_THERAPY:
            if not self.massage_type or not self.massage_duration_minutes:
                raise ValueError("massage_type and massage_duration_minutes are required")
        else:
            if not self.frequency_type:
                raise ValueError("frequency_type is required")
            if self.frequency_type == FrequencyType.DAILY and not self.daily_visits_per_day:
                raise ValueError("daily_visits_per_day is required for daily frequency")
        return self


class PricingQuoteResponse(BaseModel):
    visit_fee: int
    machine_charge: int
    total_amount: int
    platform_fee_percent: int
    platform_fee_amount: int
    therapist_payout: int


class TherapyBookingPaymentInit(BaseModel):
    """Returned right after booking creation to drive the Razorpay checkout widget."""

    booking: "TherapyBookingResponse"
    razorpay_order_id: str
    razorpay_key_id: str
    amount: int
    currency: str = "INR"


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class TherapyBookingStatusUpdate(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class TherapyBookingAssign(BaseModel):
    assigned_staff_id: str
    assigned_staff_name: str
    #: Optional slot from the *new* therapist's calendar. When given, the
    #: booking is re-timed to it and the previous therapist's slot is released.
    slot_id: Optional[str] = None


class TherapyBookingResponse(IdTimestampSchema):
    reference: str
    patient_id: Optional[str] = None
    patient_name: str
    patient_age: Optional[int] = None
    patient_gender: Optional[Gender] = None
    contact_phone: str
    contact_email: Optional[EmailStr] = None

    address: str
    city: Optional[str] = None
    pincode: Optional[str] = None

    service_category: ServiceCategory
    condition_notes: Optional[str] = None

    preferred_date: dt.date
    shift: Shift
    time_slot: str
    session_duration_minutes: int

    frequency_type: Optional[FrequencyType] = None
    daily_visits_per_day: Optional[int] = None
    weekly_days_count: Optional[int] = None
    package_duration: Optional[PackageDuration] = None
    package_custom_months: Optional[int] = None
    equipment: List[EquipmentCode] = Field(default_factory=list)
    equipment_items: List[BookedEquipment] = Field(default_factory=list)
    slot_id: Optional[str] = None

    massage_type: Optional[MassageType] = None
    massage_duration_minutes: Optional[int] = None

    visit_fee: int
    machine_charge: int
    total_amount: int
    platform_fee_percent: int
    platform_fee_amount: int
    therapist_payout: int

    payment_status: PaymentStatus
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    amount_paid: int

    cancellation_reason: Optional[str] = None
    cancelled_by: Optional[str] = None
    refund_amount: int = 0
    razorpay_refund_id: Optional[str] = None
    refunded_at: Optional[dt.datetime] = None

    status: BookingStatus
    assigned_staff_id: Optional[str] = None
    assigned_staff_name: Optional[str] = None
    admin_notes: Optional[str] = None


TherapyBookingPaymentInit.model_rebuild()
