"""FastAPI dependency-injection providers."""

from app.dependencies.auth import (
    ActorContext,
    get_actor,
    get_current_active_user,
    get_current_user,
    require_permission,
    require_superuser,
)

__all__ = [
    "ActorContext",
    "get_actor",
    "get_current_user",
    "get_current_active_user",
    "require_permission",
    "require_superuser",
]
