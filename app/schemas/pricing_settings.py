"""Pricing & refund policy settings schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import IdTimestampSchema


class PricingSettingsUpdate(BaseModel):
    daily_visit_fee_1: Optional[int] = Field(None, ge=0)
    daily_visit_fee_2: Optional[int] = Field(None, ge=0)
    daily_visit_fee_3: Optional[int] = Field(None, ge=0)
    flat_visit_fee: Optional[int] = Field(None, ge=0)
    machine_charge_per_unit: Optional[int] = Field(None, ge=0)
    massage_normal_oil_fee: Optional[int] = Field(None, ge=0)
    massage_dry_fee: Optional[int] = Field(None, ge=0)
    massage_deep_tissue_fee: Optional[int] = Field(None, ge=0)
    massage_overtime_surcharge: Optional[int] = Field(None, ge=0)
    massage_standard_max_minutes: Optional[int] = Field(None, ge=1)
    platform_fee_physiotherapy_percent: Optional[int] = Field(None, ge=0, le=100)
    platform_fee_yoga_therapy_percent: Optional[int] = Field(None, ge=0, le=100)
    platform_fee_home_rehabilitation_percent: Optional[int] = Field(None, ge=0, le=100)
    platform_fee_massage_therapy_percent: Optional[int] = Field(None, ge=0, le=100)
    cancellation_full_refund_window_hours: Optional[int] = Field(None, ge=0)
    cancellation_late_refund_percent: Optional[int] = Field(None, ge=0, le=100)


class PricingSettingsResponse(IdTimestampSchema):
    daily_visit_fee_1: int
    daily_visit_fee_2: int
    daily_visit_fee_3: int
    flat_visit_fee: int
    machine_charge_per_unit: int
    massage_normal_oil_fee: int
    massage_dry_fee: int
    massage_deep_tissue_fee: int
    massage_overtime_surcharge: int
    massage_standard_max_minutes: int
    platform_fee_physiotherapy_percent: int
    platform_fee_yoga_therapy_percent: int
    platform_fee_home_rehabilitation_percent: int
    platform_fee_massage_therapy_percent: int
    cancellation_full_refund_window_hours: int
    cancellation_late_refund_percent: int
