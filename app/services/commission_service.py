"""Commission tracking business logic.

Handles crediting therapist earnings when bookings complete, reversing
them on cancellation, computing per-therapist summaries, and managing
admin-initiated payout settlements.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.logging import get_logger
from app.models.base import utcnow
from app.models.enums import EarningStatus, PayoutStatus
from app.models.therapist_earning import TherapistEarning
from app.models.therapist_payout import TherapistPayout
from app.models.therapy_booking import TherapyBooking
from app.models.user import User

logger = get_logger(__name__)


class CommissionService:
    """Manages the lifecycle of therapist earnings and admin payouts."""

    # ── Credit / Reverse ────────────────────────────────────────────

    async def credit_earning(self, booking: TherapyBooking) -> Optional[TherapistEarning]:
        """Create an earning record when a booking is COMPLETED + PAID.

        Idempotent — silently returns the existing record if one already
        exists for this booking.
        """
        if not booking.assigned_staff_id:
            logger.warning("credit_earning skipped: no assigned_staff_id on %s", booking.reference)
            return None

        # Check idempotency
        existing = await TherapistEarning.find_one({"booking_id": str(booking.id)})
        if existing:
            logger.info("Earning already exists for booking %s", booking.reference)
            return existing

        # Fetch therapist details
        therapist = await User.get(booking.assigned_staff_id)
        therapist_name = therapist.name if therapist else (booking.assigned_staff_name or "Unknown")
        therapist_email = therapist.email if therapist else None

        earning = TherapistEarning(
            therapist_id=booking.assigned_staff_id,
            therapist_name=therapist_name,
            therapist_email=therapist_email,
            booking_id=str(booking.id),
            booking_reference=booking.reference,
            service_category=booking.service_category.value if hasattr(booking.service_category, "value") else str(booking.service_category),
            patient_name=booking.patient_name,
            total_amount=booking.total_amount,
            platform_fee_percent=booking.platform_fee_percent,
            platform_fee_amount=booking.platform_fee_amount,
            therapist_payout=booking.therapist_payout,
            status=EarningStatus.PENDING,
            booking_completed_at=utcnow(),
        )
        await earning.insert()
        logger.info(
            "Credited Rs.%d earning for therapist %s on booking %s",
            earning.therapist_payout, therapist_name, booking.reference,
        )
        return earning

    async def reverse_earning(self, booking_id: str) -> Optional[TherapistEarning]:
        """Mark an earning as REVERSED when a completed booking is cancelled.

        Only reverses ``pending`` earnings — settled ones cannot be reversed
        (the admin would need to handle those manually).
        """
        earning = await TherapistEarning.find_one({"booking_id": booking_id})
        if not earning:
            return None

        if earning.status == EarningStatus.REVERSED:
            return earning  # Already reversed

        if earning.status == EarningStatus.SETTLED:
            logger.warning(
                "Cannot auto-reverse settled earning %s — admin must handle payout adjustment manually",
                str(earning.id),
            )
            return earning

        earning.status = EarningStatus.REVERSED
        earning.reversed_at = utcnow()
        earning.notes = (earning.notes or "") + "\n[Auto-reversed: booking cancelled/rejected]"
        earning.touch()
        await earning.save()

        logger.info("Reversed earning for booking %s", booking_id)
        return earning

    # ── Therapist Self-Service Queries ───────────────────────────────

    async def get_therapist_earnings(
        self,
        therapist_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[TherapistEarning], int]:
        """List earnings for a specific therapist, optionally filtered by status."""
        query: Dict[str, Any] = {"therapist_id": therapist_id}
        if status:
            query["status"] = status
        total = await TherapistEarning.find(query).count()
        items = (
            await TherapistEarning.find(query)
            .sort("-created_at")
            .skip((page - 1) * page_size)
            .limit(page_size)
            .to_list()
        )
        return items, total

    async def get_therapist_summary(self, therapist_id: str) -> Dict[str, Any]:
        """Compute earning totals for a single therapist."""
        pipeline = [
            {"$match": {"therapist_id": therapist_id}},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "total": {"$sum": "$therapist_payout"},
                }
            },
        ]
        results = await TherapistEarning.get_motor_collection().aggregate(pipeline).to_list(10)

        summary = {
            "therapist_id": therapist_id,
            "pending_amount": 0,
            "pending_count": 0,
            "settled_amount": 0,
            "settled_count": 0,
            "reversed_amount": 0,
            "reversed_count": 0,
            "total_earned": 0,
            "total_bookings": 0,
        }
        for row in results:
            status = row["_id"]
            summary[f"{status}_amount"] = row["total"]
            summary[f"{status}_count"] = row["count"]

        summary["total_earned"] = summary["pending_amount"] + summary["settled_amount"]
        summary["total_bookings"] = summary["pending_count"] + summary["settled_count"]
        return summary

    async def get_therapist_payouts(
        self,
        therapist_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[TherapistPayout], int]:
        """List payouts for a specific therapist."""
        query = {"therapist_id": therapist_id}
        total = await TherapistPayout.find(query).count()
        items = (
            await TherapistPayout.find(query)
            .sort("-created_at")
            .skip((page - 1) * page_size)
            .limit(page_size)
            .to_list()
        )
        return items, total

    # ── Admin Queries ───────────────────────────────────────────────

    async def get_all_therapist_summaries(self) -> List[Dict[str, Any]]:
        """Admin view: aggregate earnings grouped by therapist."""
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "therapist_id": "$therapist_id",
                        "therapist_name": "$therapist_name",
                        "therapist_email": "$therapist_email",
                        "status": "$status",
                    },
                    "count": {"$sum": 1},
                    "total": {"$sum": "$therapist_payout"},
                }
            },
            {"$sort": {"_id.therapist_name": 1}},
        ]
        raw = await TherapistEarning.get_motor_collection().aggregate(pipeline).to_list(500)

        # Reshape into per-therapist summaries
        therapists: Dict[str, Dict[str, Any]] = {}
        for row in raw:
            tid = row["_id"]["therapist_id"]
            if tid not in therapists:
                therapists[tid] = {
                    "therapist_id": tid,
                    "therapist_name": row["_id"]["therapist_name"],
                    "therapist_email": row["_id"].get("therapist_email"),
                    "pending_amount": 0,
                    "pending_count": 0,
                    "settled_amount": 0,
                    "settled_count": 0,
                    "reversed_amount": 0,
                    "reversed_count": 0,
                    "total_earned": 0,
                    "total_bookings": 0,
                }
            status = row["_id"]["status"]
            therapists[tid][f"{status}_amount"] = row["total"]
            therapists[tid][f"{status}_count"] = row["count"]

        for t in therapists.values():
            t["total_earned"] = t["pending_amount"] + t["settled_amount"]
            t["total_bookings"] = t["pending_count"] + t["settled_count"]

        return sorted(therapists.values(), key=lambda x: x["pending_amount"], reverse=True)

    async def list_all_earnings(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
        therapist_id: Optional[str] = None,
    ) -> Tuple[List[TherapistEarning], int]:
        """Admin view: list all earnings with optional filters."""
        query: Dict[str, Any] = {}
        if status:
            query["status"] = status
        if therapist_id:
            query["therapist_id"] = therapist_id
        total = await TherapistEarning.find(query).count()
        items = (
            await TherapistEarning.find(query)
            .sort("-created_at")
            .skip((page - 1) * page_size)
            .limit(page_size)
            .to_list()
        )
        return items, total

    async def list_all_payouts(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
        therapist_id: Optional[str] = None,
    ) -> Tuple[List[TherapistPayout], int]:
        """Admin view: list all payouts with optional filters."""
        query: Dict[str, Any] = {}
        if status:
            query["status"] = status
        if therapist_id:
            query["therapist_id"] = therapist_id
        total = await TherapistPayout.find(query).count()
        items = (
            await TherapistPayout.find(query)
            .sort("-created_at")
            .skip((page - 1) * page_size)
            .limit(page_size)
            .to_list()
        )
        return items, total

    # ── Payout Creation & Settlement ────────────────────────────────

    async def create_payout(
        self,
        therapist_id: str,
        period_start: dt.date,
        period_end: dt.date,
        admin_id: str,
        admin_name: str,
        admin_notes: Optional[str] = None,
    ) -> TherapistPayout:
        """Create a payout and mark all matching pending earnings as settled."""
        # Fetch all pending earnings in the period
        query = {
            "therapist_id": therapist_id,
            "status": EarningStatus.PENDING.value,
            "booking_completed_at": {
                "$gte": dt.datetime.combine(period_start, dt.time.min, tzinfo=dt.timezone.utc),
                "$lte": dt.datetime.combine(period_end, dt.time.max, tzinfo=dt.timezone.utc),
            },
        }
        earnings = await TherapistEarning.find(query).to_list()

        if not earnings:
            raise BadRequestException(
                f"No pending earnings found for this therapist between {period_start} and {period_end}"
            )

        # Fetch therapist info
        therapist = await User.get(therapist_id)
        if not therapist:
            raise NotFoundException("Therapist not found")

        total_payout = sum(e.therapist_payout for e in earnings)
        earning_ids = [str(e.id) for e in earnings]

        # Format period label
        if period_start.month == period_end.month and period_start.year == period_end.year:
            period_label = period_start.strftime("%B %Y")
        else:
            period_label = f"{period_start.strftime('%d %b %Y')} — {period_end.strftime('%d %b %Y')}"

        payout = TherapistPayout(
            therapist_id=therapist_id,
            therapist_name=therapist.name,
            therapist_email=therapist.email,
            period_label=period_label,
            period_start=period_start,
            period_end=period_end,
            total_earnings=total_payout,
            total_bookings=len(earnings),
            earning_ids=earning_ids,
            status=PayoutStatus.PENDING,
            paid_by_admin_id=admin_id,
            paid_by_admin_name=admin_name,
            admin_notes=admin_notes,
        )
        await payout.insert()

        # Mark all earnings as settled
        await TherapistEarning.get_motor_collection().update_many(
            {"_id": {"$in": [e.id for e in earnings]}},
            {
                "$set": {
                    "status": EarningStatus.SETTLED.value,
                    "settled_in_payout_id": str(payout.id),
                    "updated_at": utcnow(),
                }
            },
        )

        logger.info(
            "Created payout of Rs.%d for therapist %s (%d bookings, period %s)",
            total_payout, therapist.name, len(earnings), period_label,
        )
        return payout

    async def mark_payout_paid(
        self,
        payout_id: str,
        payment_method: str,
        transaction_reference: str,
        admin_id: str,
        admin_name: str,
        admin_notes: Optional[str] = None,
    ) -> TherapistPayout:
        """Admin marks a payout as paid after manual bank/UPI transfer."""
        payout = await TherapistPayout.get(payout_id)
        if not payout:
            raise NotFoundException("Payout not found")

        if payout.status == PayoutStatus.PAID:
            raise BadRequestException("This payout is already marked as paid")

        payout.status = PayoutStatus.PAID
        payout.payment_method = payment_method
        payout.transaction_reference = transaction_reference
        payout.paid_at = utcnow()
        payout.paid_by_admin_id = admin_id
        payout.paid_by_admin_name = admin_name
        if admin_notes:
            payout.admin_notes = (
                f"{payout.admin_notes}\n{admin_notes}" if payout.admin_notes else admin_notes
            )
        payout.touch()
        await payout.save()

        logger.info("Payout %s marked as PAID (method=%s, ref=%s)", payout_id, payment_method, transaction_reference)
        return payout

    async def mark_payout_failed(
        self,
        payout_id: str,
        admin_notes: Optional[str] = None,
    ) -> TherapistPayout:
        """Admin marks a payout as failed — reverts earnings back to pending."""
        payout = await TherapistPayout.get(payout_id)
        if not payout:
            raise NotFoundException("Payout not found")

        if payout.status != PayoutStatus.PENDING:
            raise BadRequestException("Only pending payouts can be marked as failed")

        payout.status = PayoutStatus.FAILED
        if admin_notes:
            payout.admin_notes = (
                f"{payout.admin_notes}\n[FAILED] {admin_notes}" if payout.admin_notes else f"[FAILED] {admin_notes}"
            )
        payout.touch()
        await payout.save()

        # Revert earnings back to pending
        if payout.earning_ids:
            from bson import ObjectId
            await TherapistEarning.get_motor_collection().update_many(
                {"_id": {"$in": [ObjectId(eid) if len(eid) == 24 else eid for eid in payout.earning_ids]}},
                {
                    "$set": {
                        "status": EarningStatus.PENDING.value,
                        "settled_in_payout_id": None,
                        "updated_at": utcnow(),
                    }
                },
            )

        logger.info("Payout %s marked as FAILED — earnings reverted to pending", payout_id)
        return payout


commission_service = CommissionService()
