"""Seed demo therapists (+ their slots and personal equipment) for testing.

Everything created here uses the ``@demo.hpi`` email domain so it can be
removed again in one command:

    uv run python scripts/seed_test_therapists.py          # create
    uv run python scripts/seed_test_therapists.py --purge  # remove

Idempotent: running it twice will not create duplicates.

The set deliberately covers the cases the booking flow needs exercised:
* all three therapist types (physiotherapist / yoga / massage),
* both genders for massage, so gender-matching can be tested from either side,
* published home-visit slots across the next few days,
* a few therapist-owned equipment items with their own charges.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import sys

from app.core.security import hash_password
from app.database.connection import close_mongo_connection, init_database
from app.models.enums import EquipmentOwner, ServiceCategory, SlotType
from app.models.therapist_slot import TherapistSlot
from app.models.therapy_equipment import TherapyEquipment
from app.models.user import User

DEMO_DOMAIN = "demo.hpi"
DEMO_PASSWORD = "Test@12345"

# name, user_type, gender, qualification, tier, specialization, years
THERAPISTS: list[tuple[str, str, str, str, str, str, int]] = [
    # ── Physiotherapists ────────────────────────────────────────────
    ("Arindam Sen", "physiotherapist", "male", "MPT", "premium", "Orthopedic", 11),
    ("Priya Chatterjee", "physiotherapist", "female", "MPT", "premium", "Neurological", 9),
    ("Rahul Das", "physiotherapist", "male", "BPT", "verified", "Sports", 6),
    ("Sneha Roy", "physiotherapist", "female", "BPT", "verified", "Pediatric", 5),
    ("Imran Khan", "physiotherapist", "male", "DPT", "premium", "Cardiopulmonary", 12),
    ("Ananya Ghosh", "physiotherapist", "female", "MPT", "verified", "Geriatric", 8),
    ("Sourav Mondal", "physiotherapist", "male", "BPT", "associate", "Orthopedic", 3),
    ("Debjani Bose", "physiotherapist", "female", "PT", "associate", "Neurological", 4),
    ("Kaushik Nag", "physiotherapist", "male", "MPT", "verified", "Sports", 7),
    ("Ritika Saha", "physiotherapist", "female", "BPT", "verified", "Geriatric", 6),
    # ── Massage therapists (both genders — gender matching) ─────────
    ("Bikram Paul", "massage_therapist", "male", "PT", "premium", "Deep Tissue", 10),
    ("Sujata Dutta", "massage_therapist", "female", "PT", "premium", "Aromatherapy", 9),
    ("Nurul Haque", "massage_therapist", "male", "PT", "verified", "Sports Massage", 7),
    ("Moumita Kar", "massage_therapist", "female", "PT", "verified", "Swedish", 6),
    ("Tapan Barman", "massage_therapist", "male", "PT", "associate", "Relaxation", 4),
    ("Ishita Sarkar", "massage_therapist", "female", "PT", "verified", "Deep Tissue", 8),
    ("Jayanta Pal", "massage_therapist", "male", "PT", "verified", "Hot Stone", 5),
    ("Payel Adhikari", "massage_therapist", "female", "PT", "associate", "Relaxation", 3),
    # ── Yoga therapists ─────────────────────────────────────────────
    ("Devdutt Joshi", "yoga_therapist", "male", "PT", "premium", "Therapeutic Yoga", 12),
    ("Meera Iyer", "yoga_therapist", "female", "PT", "premium", "Prenatal Yoga", 10),
    ("Alok Verma", "yoga_therapist", "male", "PT", "verified", "Hatha", 6),
    ("Trisha Banerjee", "yoga_therapist", "female", "PT", "verified", "Restorative", 7),
    ("Sandip Hazra", "yoga_therapist", "male", "PT", "associate", "Pranayama", 3),
    ("Nandini Sinha", "yoga_therapist", "female", "PT", "verified", "Senior Yoga", 8),
]

CATEGORY_FOR_TYPE = {
    "physiotherapist": ServiceCategory.PHYSIOTHERAPY,
    "yoga_therapist": ServiceCategory.YOGA_THERAPY,
    "massage_therapist": ServiceCategory.MASSAGE_THERAPY,
}

# Personal equipment a therapist brings, keyed by user_type.
OWN_EQUIPMENT = {
    "physiotherapist": [("Personal TENS Unit", 120), ("Kinesio Taping Kit", 80)],
    "massage_therapist": [("Portable Massage Table", 220), ("Premium Oil Kit", 140)],
    "yoga_therapist": [("Cork Yoga Blocks", 60), ("Meditation Bolster", 90)],
}

# Slot times published for each therapist, staggered so the calendars differ.
SLOT_PATTERNS = [
    [("08:00", "09:00"), ("10:00", "11:00"), ("16:00", "17:00")],
    [("09:00", "10:00"), ("13:00", "14:00"), ("18:00", "19:00")],
    [("07:00", "08:00"), ("11:00", "12:00"), ("17:00", "18:00")],
]

DAYS_AHEAD = 7


def email_for(name: str) -> str:
    return f"{name.lower().replace(' ', '.')}@{DEMO_DOMAIN}"


async def purge() -> None:
    """Remove every demo therapist and everything attached to them."""
    users = await User.find({"email": {"$regex": f"@{DEMO_DOMAIN}$"}}).to_list()
    ids = [str(u.id) for u in users]
    if not ids:
        print("Nothing to purge — no demo therapists found.")
        return

    slots = await TherapistSlot.find({"therapist_id": {"$in": ids}}).delete()
    equip = await TherapyEquipment.find({"therapist_id": {"$in": ids}}).delete()
    for u in users:
        await u.delete()

    print(f"Purged {len(ids)} demo therapists, "
          f"{getattr(slots, 'deleted_count', 0)} slots, "
          f"{getattr(equip, 'deleted_count', 0)} equipment items.")


async def seed() -> None:
    today = dt.date.today()
    created_users = created_slots = created_equipment = 0
    skipped = 0

    for index, (name, user_type, gender, qualification, tier, specialization, years) in enumerate(
        THERAPISTS
    ):
        email = email_for(name)
        user = await User.find_one({"email": email})

        if user is None:
            user = User(
                name=name,
                email=email,
                hashed_password=hash_password(DEMO_PASSWORD),
                phone=f"98{30000000 + index:08d}",
                role="therapist",
                user_type=user_type,
                gender=gender,
                qualification=qualification,
                therapist_tier=tier,
                specialization=specialization,
                experience_years=years,
                verification_status="approved",
                is_active=True,
                is_email_verified=True,
                address="Kolkata, West Bengal",
                pincode="700001",
            )
            await user.insert()
            created_users += 1
        else:
            skipped += 1

        therapist_id = str(user.id)
        category = CATEGORY_FOR_TYPE[user_type]

        # ── Home-visit slots for the next few days ──
        pattern = SLOT_PATTERNS[index % len(SLOT_PATTERNS)]
        for day in range(1, DAYS_AHEAD + 1):
            date_str = (today + dt.timedelta(days=day)).isoformat()
            for start, end in pattern:
                exists = await TherapistSlot.find_one(
                    {
                        "therapist_id": therapist_id,
                        "slot_type": SlotType.HOME_VISIT.value,
                        "date": date_str,
                        "start_time": start,
                    }
                )
                if exists:
                    continue
                await TherapistSlot(
                    therapist_id=therapist_id,
                    therapist_name=user.name,
                    slot_type=SlotType.HOME_VISIT,
                    date=date_str,
                    start_time=start,
                    end_time=end,
                ).insert()
                created_slots += 1

        # ── A couple of personally-owned equipment items ──
        for item_name, charge in OWN_EQUIPMENT[user_type]:
            slug = f"{item_name.lower().replace(' ', '-')}-{therapist_id[-6:]}"
            if await TherapyEquipment.find_one({"slug": slug}):
                continue
            await TherapyEquipment(
                name=item_name,
                slug=slug,
                description=f"{user.name}'s own equipment",
                category=category,
                charge=charge,
                owner_type=EquipmentOwner.THERAPIST,
                therapist_id=therapist_id,
                therapist_name=user.name,
            ).insert()
            created_equipment += 1

    print(
        f"Done. Therapists created: {created_users} (already existed: {skipped}). "
        f"Slots created: {created_slots}. Personal equipment created: {created_equipment}."
    )
    print(f"All demo accounts use the password: {DEMO_PASSWORD}")


async def main() -> None:
    await init_database()
    try:
        if "--purge" in sys.argv:
            await purge()
        else:
            await seed()
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
