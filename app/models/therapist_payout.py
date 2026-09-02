"""Monthly/bulk admin-to-therapist payout settlement record.

Admin reviews accumulated :class:`TherapistEarning` entries, creates a
payout for a date range, manually transfers money via bank/UPI, then
records the transaction details here.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

import pymongo
from pydantic import Field

from app.models.base import TimestampedDocument, utcnow
from app.models.enums import PayoutStatus


class TherapistPayout(TimestampedDocument):
    """A bulk settlement record for paying a therapist their accumulated earnings."""

    therapist_id: str
    therapist_name: str
    therapist_email: Optional[str] = None

    # Settlement period
    period_label: str                     # e.g. "September 2026"
    period_start: dt.date
    period_end: dt.date

    # Aggregated totals
    total_earnings: int = 0               # Sum of therapist_payout for settled earnings (Rs.)
    total_bookings: int = 0               # Number of earnings settled in this payout
    earning_ids: list[str] = Field(default_factory=list)  # TherapistEarning._id list

    status: PayoutStatus = PayoutStatus.PENDING

    # Admin fills these after manual transfer
    payment_method: Optional[str] = None  # "bank_transfer" | "upi" | "cash" | "other"
    transaction_reference: Optional[str] = None  # UTR / UPI ref / receipt number
    paid_at: Optional[dt.datetime] = None
    paid_by_admin_id: Optional[str] = None
    paid_by_admin_name: Optional[str] = None
    admin_notes: Optional[str] = None

    class Settings:
        name = "therapist_payouts"
        indexes = [
            [("therapist_id", pymongo.ASCENDING), ("period_start", pymongo.ASCENDING)],
            [("status", pymongo.ASCENDING)],
            [("created_at", pymongo.DESCENDING)],
        ]
