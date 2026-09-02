"""Pricing engine tests — verify the exact worked examples from the spec."""

import pytest

from app.core.exceptions import BadRequestException
from app.models.enums import EquipmentCode, FrequencyType, MassageType, ServiceCategory
from app.services import pricing_service


def test_daily_visit_pricing_without_machine():
    r = pricing_service.price_visit_booking(
        service_category=ServiceCategory.PHYSIOTHERAPY,
        frequency_type=FrequencyType.DAILY,
        daily_visits_per_day=1,
        equipment=[],
    )
    assert r.visit_fee == 400
    assert r.machine_charge == 0
    assert r.total_amount == 400
    assert r.platform_fee_percent == 20
    assert r.platform_fee_amount == 80
    assert r.therapist_payout == 320


def test_daily_visit_pricing_tiers():
    assert pricing_service.price_visit_booking(
        service_category=ServiceCategory.PHYSIOTHERAPY, frequency_type=FrequencyType.DAILY,
        daily_visits_per_day=2, equipment=[],
    ).visit_fee == 600
    assert pricing_service.price_visit_booking(
        service_category=ServiceCategory.PHYSIOTHERAPY, frequency_type=FrequencyType.DAILY,
        daily_visits_per_day=3, equipment=[],
    ).visit_fee == 800


def test_one_machine_pricing():
    r = pricing_service.price_visit_booking(
        service_category=ServiceCategory.PHYSIOTHERAPY,
        frequency_type=FrequencyType.DAILY,
        daily_visits_per_day=1,
        equipment=[EquipmentCode.IFT],
    )
    assert r.visit_fee == 400
    assert r.machine_charge == 100
    assert r.total_amount == 500
    assert r.platform_fee_amount == 100
    assert r.therapist_payout == 400


def test_two_machines_pricing():
    r = pricing_service.price_visit_booking(
        service_category=ServiceCategory.PHYSIOTHERAPY,
        frequency_type=FrequencyType.DAILY,
        daily_visits_per_day=1,
        equipment=[EquipmentCode.IFT, EquipmentCode.TENS],
    )
    assert r.machine_charge == 200
    assert r.total_amount == 600
    assert r.platform_fee_amount == 120
    assert r.therapist_payout == 480


def test_weekly_pricing_is_flat_400_per_visit():
    r = pricing_service.price_visit_booking(
        service_category=ServiceCategory.PHYSIOTHERAPY,
        frequency_type=FrequencyType.WEEKLY,
        daily_visits_per_day=None,
        equipment=[],
    )
    assert r.visit_fee == 400


def test_package_pricing_includes_machine_use():
    r = pricing_service.price_visit_booking(
        service_category=ServiceCategory.PHYSIOTHERAPY,
        frequency_type=FrequencyType.PACKAGE,
        daily_visits_per_day=None,
        equipment=[EquipmentCode.IFT, EquipmentCode.UST],
    )
    assert r.visit_fee == 400
    assert r.machine_charge == 0  # machine use is bundled into the package rate
    assert r.total_amount == 400
    assert r.platform_fee_amount == 80
    assert r.therapist_payout == 320


def test_home_rehabilitation_uses_35_percent_commission():
    r = pricing_service.price_visit_booking(
        service_category=ServiceCategory.HOME_REHABILITATION,
        frequency_type=FrequencyType.DAILY,
        daily_visits_per_day=1,
        equipment=[],
    )
    assert r.platform_fee_percent == 35
    assert r.platform_fee_amount == 140
    assert r.therapist_payout == 260


@pytest.mark.parametrize(
    "massage_type,duration,expected_fee",
    [
        (MassageType.NORMAL_OIL, 50, 800),
        (MassageType.DRY, 50, 900),
        (MassageType.DEEP_TISSUE, 50, 1000),
        (MassageType.NORMAL_OIL, 75, 900),  # over 60 min => +100 surcharge
    ],
)
def test_massage_pricing(massage_type, duration, expected_fee):
    r = pricing_service.price_massage_booking(massage_type=massage_type, massage_duration_minutes=duration)
    assert r.visit_fee == expected_fee
    assert r.machine_charge == 0
    assert r.platform_fee_percent == 35


def test_invalid_daily_visits_per_day_rejected():
    with pytest.raises(BadRequestException):
        pricing_service.price_visit_booking(
            service_category=ServiceCategory.PHYSIOTHERAPY,
            frequency_type=FrequencyType.DAILY,
            daily_visits_per_day=5,
            equipment=[],
        )


def test_massage_pricing_rejects_visit_pricer():
    with pytest.raises(BadRequestException):
        pricing_service.price_visit_booking(
            service_category=ServiceCategory.MASSAGE_THERAPY,
            frequency_type=FrequencyType.DAILY,
            daily_visits_per_day=1,
            equipment=[],
        )
