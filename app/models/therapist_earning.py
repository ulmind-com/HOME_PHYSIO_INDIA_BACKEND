"""Per-booking commission credit for a therapist.

Each record tracks the platform commission split for a single completed
therapy booking. Records start as ``pending``, move to ``settled`` when
included in a :class:`TherapistPayout`, and may be ``reversed`` if the
booking is later cancelled/rejected.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

import pymongo
from pydantic import Field

from app.models.base import TimestampedDocument, utcnow
from app.models.enums import EarningStatus


class TherapistEarning(TimestampedDocument):
    """A single commission credit linked to a completed therapy booking."""

    therapist_id: str
    therapist_name: str
    therapist_email: Optional[str] = None

    booking_id: str
    booking_reference: str
    service_category: str
    patient_name: str

    # Monetary breakdown (all in Rs.)
    total_amount: int = 0
    platform_fee_percent: int = 0
    platform_fee_amount: int = 0
    therapist_payout: int = 0

    status: EarningStatus = EarningStatus.PENDING
    settled_in_payout_id: Optional[str] = None

    booking_completed_at: Optional[dt.datetime] = None
    reversed_at: Optional[dt.datetime] = None
    notes: Optional[str] = None

    class Settings:
        name = "therapist_earnings"
        indexes = [
            [("therapist_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)],
            [("booking_id", pymongo.ASCENDING)],
            [("status", pymongo.ASCENDING)],
            [("created_at", pymongo.DESCENDING)],
        ]
