"""Dashboard analytics service (counts, recent activity, charts data)."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from app.models.blog import Blog
from app.models.booking import Booking
from app.models.career import JobApplication
from app.models.contact import ContactMessage
from app.models.enums import BookingStatus
from app.models.equipment import Equipment, EquipmentRental
from app.models.service import Service


class DashboardService:
    """Aggregate cross-collection statistics for the admin dashboard."""

    async def stats(self) -> Dict[str, Any]:
        """Return top-line counts used by dashboard stat cards."""
        (
            total_bookings,
            pending_bookings,
            approved_bookings,
            completed_bookings,
            total_services,
            total_equipment,
            total_rentals,
            total_applications,
            new_contacts,
            total_blogs,
        ) = (
            await Booking.find({}).count(),
            await Booking.find({"status": BookingStatus.PENDING}).count(),
            await Booking.find({"status": BookingStatus.APPROVED}).count(),
            await Booking.find({"status": BookingStatus.COMPLETED}).count(),
            await Service.find({}).count(),
            await Equipment.find({}).count(),
            await EquipmentRental.find({}).count(),
            await JobApplication.find({}).count(),
            await ContactMessage.find({"status": "new"}).count(),
            await Blog.find({}).count(),
        )
        return {
            "bookings": {
                "total": total_bookings,
                "pending": pending_bookings,
                "approved": approved_bookings,
                "completed": completed_bookings,
            },
            "services": total_services,
            "equipment": total_equipment,
            "rentals": total_rentals,
            "applications": total_applications,
            "new_contacts": new_contacts,
            "blogs": total_blogs,
            # Revenue is a placeholder until a payments integration exists.
            "revenue": {"currency": "INR", "total": 0, "note": "placeholder"},
        }

    async def booking_status_breakdown(self) -> Dict[str, int]:
        """Return a count per booking status (for a pie/donut chart)."""
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        result = await Booking.aggregate(pipeline).to_list()
        breakdown = {status.value: 0 for status in BookingStatus}
        for row in result:
            breakdown[row["_id"]] = row["count"]
        return breakdown

    async def bookings_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """Return a daily booking count for the last ``days`` days."""
        since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
        pipeline = [
            {"$match": {"created_at": {"$gte": since}}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        result = await Booking.aggregate(pipeline).to_list()
        return [{"date": row["_id"], "count": row["count"]} for row in result]

    async def recent_bookings(self, limit: int = 5) -> List[Booking]:
        return await Booking.find({}).sort([("created_at", -1)]).limit(limit).to_list()

    async def recent_contacts(self, limit: int = 5) -> List[ContactMessage]:
        return (
            await ContactMessage.find({}).sort([("created_at", -1)]).limit(limit).to_list()
        )

    async def recent_applications(self, limit: int = 5) -> List[JobApplication]:
        return (
            await JobApplication.find({}).sort([("created_at", -1)]).limit(limit).to_list()
        )


dashboard_service = DashboardService()
