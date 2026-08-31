"""Idempotent database seeding: permissions, roles and the bootstrap admin."""

from __future__ import annotations

from app.config import settings
from app.core.logging import get_logger
from app.core.permissions import DEFAULT_ROLES, all_permission_codes
from app.core.security import hash_password
from app.models.rbac import Permission, Role
from app.models.user import User
from app.models.user_type import UserType

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
        {"name": "Patient", "slug": "patient", "description": "Patient Account"}
    ]
    for ct in core_types:
        if await UserType.find_one({"slug": ct["slug"]}) is None:
            await UserType(name=ct["name"], slug=ct["slug"], description=ct["description"], is_core=True).insert()
            logger.info("Seeded core user type", extra={"slug": ct["slug"]})


async def run_seed() -> None:
    """Run all seeders in order (safe to run on every startup)."""
    await seed_permissions()
    await seed_roles()
    await seed_user_types()
    await seed_admin()
