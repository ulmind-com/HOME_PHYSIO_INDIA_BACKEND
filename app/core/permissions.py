"""Central catalogue of permission codes and default role definitions.

Permissions follow the ``resource:action`` convention. Roles are seeded from
:data:`DEFAULT_ROLES` on first startup.
"""

from __future__ import annotations

from typing import Dict, List

# ---- Actions ----
VIEW = "view"
CREATE = "create"
UPDATE = "update"
DELETE = "delete"
MANAGE = "manage"  # implies full control of a resource

# ---- Resources ----
RESOURCES = [
    "dashboard",
    "users",
    "roles",
    "services",
    "categories",
    "bookings",
    "patients",
    "equipment",
    "rentals",
    "careers",
    "applications",
    "blogs",
    "videos",
    "testimonials",
    "faqs",
    "contacts",
    "settings",
    "seo",
    "media",
    "notifications",
    "activity_logs",
    "medical_reports",
]


def _perm(resource: str, action: str) -> str:
    return f"{resource}:{action}"


def all_permission_codes() -> List[str]:
    """Return every permission code in the system."""
    codes: List[str] = []
    for resource in RESOURCES:
        codes.append(_perm(resource, VIEW))
        codes.append(_perm(resource, CREATE))
        codes.append(_perm(resource, UPDATE))
        codes.append(_perm(resource, DELETE))
    return codes


# Wildcard granting all permissions (checked specially in the dependency).
ALL = "*"

# ---- Default roles seeded at startup ----
DEFAULT_ROLES: Dict[str, dict] = {
    "super_admin": {
        "name": "Super Admin",
        "description": "Full unrestricted access to everything.",
        "permissions": [ALL],
        "is_system": True,
    },
    "admin": {
        "name": "Administrator",
        "description": "Manage all operational content and requests.",
        "permissions": [
            code
            for code in all_permission_codes()
            if not code.startswith(("users:", "roles:", "settings:delete"))
        ],
        "is_system": True,
    },
    "editor": {
        "name": "Content Editor",
        "description": "Manage marketing content (services, blogs, videos, FAQs).",
        "permissions": [
            _perm(r, a)
            for r in ("services", "categories", "blogs", "videos", "testimonials", "faqs")
            for a in (VIEW, CREATE, UPDATE)
        ]
        + [_perm("dashboard", VIEW), _perm("media", CREATE), _perm("media", VIEW)],
        "is_system": True,
    },
    "support": {
        "name": "Support Agent",
        "description": "Handle bookings, rentals, contacts and applications.",
        "permissions": [
            _perm(r, a)
            for r in ("bookings", "rentals", "contacts", "applications", "patients", "medical_reports")
            for a in (VIEW, UPDATE)
        ]
        + [_perm("dashboard", VIEW), _perm("notifications", VIEW)],
        "is_system": True,
    },
    "therapist": {
        "name": "Therapist",
        "description": "Handle assigned bookings and patient reports.",
        "permissions": [
            _perm("dashboard", VIEW),
            _perm("bookings", VIEW),
            _perm("bookings", UPDATE),
            _perm("medical_reports", VIEW),
            _perm("medical_reports", UPDATE),
            _perm("patients", VIEW),
            _perm("notifications", VIEW),
        ],
        "is_system": True,
    },
}
