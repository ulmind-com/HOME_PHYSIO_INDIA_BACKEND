"""Idempotent database seeding: permissions, roles and the bootstrap admin."""

from __future__ import annotations

from app.config import settings
from app.core.logging import get_logger
from app.core.permissions import DEFAULT_ROLES, all_permission_codes
from app.core.security import hash_password
from app.models.rbac import Permission, Role
from app.models.user import User
from app.models.user_type import UserType
from app.models.service import Service
from app.models.equipment import Equipment

logger = get_logger(__name__)


async def seed_permissions() -> None:
    """Ensure every catalogue permission exists as a document."""
    existing = {p.code for p in await Permission.find_all().to_list()}
    to_create = []
    for code in all_permission_codes():
        if code in existing:
            continue
        resource, action = code.split(":", 1)
        to_create.append(
            Permission(
                code=code,
                name=f"{action.capitalize()} {resource}",
                description=f"Allows the user to {action} {resource}",
                group=resource,
            )
        )
    if to_create:
        await Permission.insert_many(to_create)
        logger.info("Seeded permissions", extra={"count": len(to_create)})


async def seed_roles() -> None:
    """Ensure the default system roles exist."""
    for slug, spec in DEFAULT_ROLES.items():
        role = await Role.find_one({"slug": slug})
        if role is None:
            await Role(
                slug=slug,
                name=spec["name"],
                description=spec["description"],
                permissions=spec["permissions"],
                is_system=spec.get("is_system", False),
            ).insert()
            logger.info("Seeded role", extra={"role": slug})
        else:
            # Keep system-role permissions in sync with the catalogue.
            if role.is_system and role.permissions != spec["permissions"]:
                role.permissions = spec["permissions"]
                role.touch()
                await role.save()


async def seed_admin() -> None:
    """Create the bootstrap super-admin user if none exists."""
    email = settings.FIRST_ADMIN_EMAIL.lower().strip()
    user = await User.find_one({"email": email})
    if user is not None:
        if not user.is_email_verified:
            user.is_email_verified = True
            await user.save()
            logger.info("Updated bootstrap admin to verified", extra={"email": email})
        return
    await User(
        name=settings.FIRST_ADMIN_NAME,
        email=email,
        hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
        role="super_admin",
        is_active=True,
        is_superuser=True,
        is_email_verified=True,
    ).insert()
    logger.info("Seeded bootstrap admin", extra={"email": email})


async def seed_user_types() -> None:
    """Ensure core user types exist."""
    core_types = [
        {"name": "Admin", "slug": "admin", "description": "System Administrator"},
        {"name": "Patient", "slug": "patient", "description": "Patient Account"},
        {"name": "Physiotherapist", "slug": "physiotherapist", "description": "Licensed Physiotherapy Specialist"},
        {"name": "Yoga Therapist", "slug": "yoga_therapist", "description": "Certified Yoga & Wellness Practitioner"},
        {"name": "Massage Therapist", "slug": "massage_therapist", "description": "Therapeutic Massage Practitioner"},
    ]
    for ct in core_types:
        if await UserType.find_one({"slug": ct["slug"]}) is None:
            await UserType(name=ct["name"], slug=ct["slug"], description=ct["description"], is_core=True).insert()
            logger.info("Seeded core user type", extra={"slug": ct["slug"]})


async def seed_services() -> None:
    """Seed the four core services from the business plan."""
    services_data = [
        {
            "title": "Home Visit Physiotherapy",
            "slug": "physiotherapy",
            "short_description": "Clinic-grade recovery, at your bedside",
            "description": (
                "A verified physiotherapist visits your home with portable modalities, "
                "assesses your condition and delivers a structured 40\u201360 minute session. "
                "Choose daily visits, a weekly rhythm, or a long-term package."
            ),
            "features": [
                "40\u201360 minute assessed session",
                "Portable IFT, TENS, UST, NMES and more",
                "Daily, weekly or package frequency",
                "Machine charges shown before you pay",
            ],
            "price": 400,
            "price_unit": "per visit",
            "is_featured": True,
            "order": 1,
        },
        {
            "title": "Home Visit Yoga Therapy",
            "slug": "yoga-therapy",
            "short_description": "Therapeutic yoga, guided one-to-one",
            "description": (
                "Condition-specific yoga therapy at home \u2014 breathing work, mobility and "
                "graded strengthening designed around your medical history rather than a generic class."
            ),
            "features": [
                "One-to-one therapeutic sessions",
                "Built around your condition, not a class plan",
                "Daily, weekly or package frequency",
                "Progress reviewed every visit",
            ],
            "price": 400,
            "price_unit": "per visit",
            "is_featured": True,
            "order": 2,
        },
        {
            "title": "Home Visit Massage Therapy",
            "slug": "massage-therapy",
            "short_description": "Clinical massage, strictly professional",
            "description": (
                "Oil, dry and deep tissue massage delivered at home by a gender-matched "
                "therapist under a strict professional-conduct policy."
            ),
            "features": [
                "Normal oil, dry and deep tissue options",
                "45\u201360 minutes standard duration",
                "Gender-matched therapist, always",
                "Zero-tolerance professional conduct policy",
            ],
            "price": 800,
            "price_unit": "per visit",
            "is_featured": True,
            "order": 3,
        },
        {
            "title": "Home Rehabilitation",
            "slug": "home-rehabilitation",
            "short_description": "Intensive recovery programmes at home",
            "description": (
                "Specialised, higher-intensity rehabilitation for stroke, post-surgical "
                "and complex neurological recovery \u2014 delivered as a supervised programme "
                "rather than single visits."
            ),
            "features": [
                "Stroke and post-surgery recovery",
                "Intensive, supervised programmes",
                "Full portable modality access",
                "Progress tracked across the programme",
            ],
            "price": 400,
            "price_unit": "per visit",
            "is_featured": True,
            "order": 4,
        },
    ]
    for s in services_data:
        if await Service.find_one({"slug": s["slug"]}) is None:
            await Service(**s).insert()
            logger.info("Seeded service", extra={"slug": s["slug"]})


async def seed_equipment() -> None:
    """Seed the nine portable modality equipment items."""
    equipment_data = [
        {
            "name": "IFT",
            "slug": "ift",
            "short_description": "Interferential Therapy",
            "description": "Deep pain relief \u2014 back, neck and joint pain",
            "rental_price": 100,
            "rental_unit": "per visit",
            "is_available": True,
            "is_featured": True,
            "order": 1,
        },
        {
            "name": "TENS",
            "slug": "tens",
            "short_description": "Transcutaneous Electrical Nerve Stimulation",
            "description": "Nerve pain modulation and acute pain control",
            "rental_price": 100,
            "rental_unit": "per visit",
            "is_available": True,
            "is_featured": True,
            "order": 2,
        },
        {
            "name": "UST",
            "slug": "ust",
            "short_description": "Ultrasound Therapy",
            "description": "Soft tissue healing \u2014 knee pain, tendon injury",
            "rental_price": 100,
            "rental_unit": "per visit",
            "is_available": True,
            "is_featured": True,
            "order": 3,
        },
        {
            "name": "NMES",
            "slug": "nmes",
            "short_description": "Neuromuscular Electrical Stimulation",
            "description": "Muscle re-education and weakness",
            "rental_price": 100,
            "rental_unit": "per visit",
            "is_available": True,
            "is_featured": True,
            "order": 4,
        },
        {
            "name": "FES",
            "slug": "fes",
            "short_description": "Functional Electrical Stimulation",
            "description": "Functional movement retraining after stroke",
            "rental_price": 100,
            "rental_unit": "per visit",
            "is_available": True,
            "is_featured": True,
            "order": 5,
        },
        {
            "name": "Portable EMS",
            "slug": "portable-ems",
            "short_description": "Electrical Muscle Stimulation",
            "description": "Muscle strengthening and atrophy prevention",
            "rental_price": 100,
            "rental_unit": "per visit",
            "is_available": True,
            "is_featured": True,
            "order": 6,
        },
        {
            "name": "Wax Bath",
            "slug": "wax-bath",
            "short_description": "Paraffin Wax Therapy",
            "description": "Joint stiffness, arthritis of hands and feet",
            "rental_price": 100,
            "rental_unit": "per visit",
            "is_available": True,
            "is_featured": True,
            "order": 7,
        },
        {
            "name": "Hot / Cold Therapy",
            "slug": "hot-cold-therapy",
            "short_description": "Thermotherapy & Cryotherapy",
            "description": "Swelling, inflammation and muscle spasm",
            "rental_price": 100,
            "rental_unit": "per visit",
            "is_available": True,
            "is_featured": True,
            "order": 8,
        },
        {
            "name": "TheraBand",
            "slug": "theraband",
            "short_description": "Resistance Band Training",
            "description": "Graded strengthening and mobility work",
            "rental_price": 100,
            "rental_unit": "per visit",
            "is_available": True,
            "is_featured": True,
            "order": 9,
        },
    ]
    for eq in equipment_data:
        if await Equipment.find_one({"slug": eq["slug"]}) is None:
            await Equipment(**eq).insert()
            logger.info("Seeded equipment", extra={"slug": eq["slug"]})


async def run_seed() -> None:
    """Run all seeders in order (safe to run on every startup)."""
    await seed_permissions()
    await seed_roles()
    await seed_user_types()
    await seed_admin()
    await seed_services()
    await seed_equipment()
