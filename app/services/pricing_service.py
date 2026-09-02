"""Pure pricing calculations for therapy bookings.

Every rate (visit fees, machine charge, massage fees, commission percentages)
is admin-configurable via :class:`app.models.pricing_settings.PricingSettings`
(see the ``/settings/pricing`` endpoint) rather than hardcoded here — these
functions just apply whatever ``rates`` they're given, so a rate change in
the admin dashboard takes effect immediately with no code deploy.

Business rules implemented (values are the shipped defaults, editable by
admin):
- Daily physiotherapy visits: 1/2/3 per day -> Rs.400 / 600 / 800.
- Weekly or package visits: flat Rs.400/visit.
- Massage: Rs.800 (normal oil) / 900 (dry) / 1000 (deep tissue),
  +Rs.100 if the session runs past 60 minutes.
- Portable equipment: +Rs.100/machine, waived when the visit is billed as
  part of a package (package fee already includes machine use).
- Platform commission: 20% for physiotherapy/yoga (visit or package),
  35% for home rehabilitation and massage therapy.

The spec doesn't give separate numbers for Yoga Therapy, so it is priced
identically to Physiotherapy (same visit engine, same commission rate) as
the closest reasonable reading of the document. Every booking is charged
per single visit/session at confirmation time — a weekly/package selection
just records the patient's committed cadence for scheduling; it does not
(yet) mean multiple visits are billed in one transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.core.exceptions import BadRequestException
from app.models.enums import EquipmentCode, FrequencyType, MassageType, ServiceCategory
from app.models.pricing_settings import PricingSettings


@dataclass(frozen=True)
class PricingResult:
    visit_fee: int
    machine_charge: int
    total_amount: int
    platform_fee_percent: int
    platform_fee_amount: int
    therapist_payout: int


def _round_half_up(value: float) -> int:
    return int(value + 0.5)


def _platform_fee_percent(rates: PricingSettings, service_category: ServiceCategory) -> int:
    return {
        ServiceCategory.PHYSIOTHERAPY: rates.platform_fee_physiotherapy_percent,
        ServiceCategory.YOGA_THERAPY: rates.platform_fee_yoga_therapy_percent,
        ServiceCategory.HOME_REHABILITATION: rates.platform_fee_home_rehabilitation_percent,
        ServiceCategory.MASSAGE_THERAPY: rates.platform_fee_massage_therapy_percent,
    }[service_category]


def price_visit_booking(
    *,
    service_category: ServiceCategory,
    frequency_type: FrequencyType,
    daily_visits_per_day: Optional[int],
    equipment: List[EquipmentCode],
    rates: Optional[PricingSettings] = None,
) -> PricingResult:
    """Price a Physiotherapy / Yoga Therapy / Home Rehabilitation visit."""
    rates = rates or PricingSettings()
    if service_category == ServiceCategory.MASSAGE_THERAPY:
        raise BadRequestException("Use price_massage_booking for massage therapy")

    daily_fee = {1: rates.daily_visit_fee_1, 2: rates.daily_visit_fee_2, 3: rates.daily_visit_fee_3}

    if frequency_type == FrequencyType.DAILY:
        if daily_visits_per_day not in daily_fee:
            raise BadRequestException("daily_visits_per_day must be 1, 2 or 3")
        visit_fee = daily_fee[daily_visits_per_day]
    elif frequency_type in (FrequencyType.WEEKLY, FrequencyType.PACKAGE):
        visit_fee = rates.flat_visit_fee
    else:
        raise BadRequestException("Invalid frequency_type")

    # Package pricing already includes applicable machine use.
    is_package = frequency_type == FrequencyType.PACKAGE
    machine_charge = 0 if is_package else rates.machine_charge_per_unit * len(equipment)

    return _finalize(rates, service_category, visit_fee, machine_charge)


def price_massage_booking(
    *,
    massage_type: MassageType,
    massage_duration_minutes: int,
    rates: Optional[PricingSettings] = None,
) -> PricingResult:
    """Price a Massage Therapy session (no packages, no equipment)."""
    rates = rates or PricingSettings()
    massage_fee = {
        MassageType.NORMAL_OIL: rates.massage_normal_oil_fee,
        MassageType.DRY: rates.massage_dry_fee,
        MassageType.DEEP_TISSUE: rates.massage_deep_tissue_fee,
    }
    if massage_type not in massage_fee:
        raise BadRequestException("Invalid massage_type")
    if massage_duration_minutes <= 0:
        raise BadRequestException("massage_duration_minutes must be positive")

    visit_fee = massage_fee[massage_type]
    if massage_duration_minutes > rates.massage_standard_max_minutes:
        visit_fee += rates.massage_overtime_surcharge

    return _finalize(rates, ServiceCategory.MASSAGE_THERAPY, visit_fee, machine_charge=0)


def _finalize(
    rates: PricingSettings, service_category: ServiceCategory, visit_fee: int, machine_charge: int
) -> PricingResult:
    total_amount = visit_fee + machine_charge
    percent = _platform_fee_percent(rates, service_category)
    platform_fee_amount = _round_half_up(total_amount * percent / 100)
    therapist_payout = total_amount - platform_fee_amount
    return PricingResult(
        visit_fee=visit_fee,
        machine_charge=machine_charge,
        total_amount=total_amount,
        platform_fee_percent=percent,
        platform_fee_amount=platform_fee_amount,
        therapist_payout=therapist_payout,
    )
