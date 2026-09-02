"""Admin-configurable pricing & refund policy for therapy bookings.

A singleton document (like WebsiteSettings) so admins can tune every rate
in the platform's commission spec from the dashboard without a code
deploy. Defaults match the original spec exactly.
"""

from __future__ import annotations

from app.models.base import TimestampedDocument


class PricingSettings(TimestampedDocument):
    # Daily physiotherapy/yoga/rehab visit fees (Rs.)
    daily_visit_fee_1: int = 400
    daily_visit_fee_2: int = 600
    daily_visit_fee_3: int = 800

    # Flat per-visit fee for weekly frequency and packages (Rs.)
    flat_visit_fee: int = 400

    # Portable equipment charge per machine (Rs.), waived inside packages
    machine_charge_per_unit: int = 100

    # Massage therapy base fees (Rs.)
    massage_normal_oil_fee: int = 800
    massage_dry_fee: int = 900
    massage_deep_tissue_fee: int = 1000
    massage_overtime_surcharge: int = 100
    massage_standard_max_minutes: int = 60

    # Platform commission (%)
    platform_fee_physiotherapy_percent: int = 20
    platform_fee_yoga_therapy_percent: int = 20
    platform_fee_home_rehabilitation_percent: int = 35
    platform_fee_massage_therapy_percent: int = 35

    # Cancellation & refund policy
    cancellation_full_refund_window_hours: int = 24
    cancellation_late_refund_percent: int = 0

    class Settings:
        name = "pricing_settings"
