"""Release slots held by bookings that were never paid for.

Safe to run on a schedule (e.g. every 15 minutes via cron):

    */15 * * * * cd /path/to/backend && PYTHONPATH=. uv run python scripts/release_abandoned_slots.py

The API also does this opportunistically whenever a therapist's availability
is browsed, so this script is a backstop for quiet periods.
"""

from __future__ import annotations

import asyncio

from app.database.connection import close_mongo_connection, init_database
from app.services.therapy_booking_service import therapy_booking_service


async def main() -> None:
    await init_database()
    try:
        released = await therapy_booking_service.release_abandoned_slots()
        print(f"Released {released} abandoned slot hold(s).")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
