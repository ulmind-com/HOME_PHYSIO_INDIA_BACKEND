"""User & role management endpoints (superuser / users:* permissions)."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks, Query
import string
import secrets

from app.api.helpers import item_response, paginated_response
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.core.pagination import PaginationParams, pagination_params
from app.core.permissions import all_permission_codes
from app.core.responses import success_response
from app.core.security import hash_password
from app.dependencies.auth import ActorContext, require_permission
from app.models.enums import ActivityAction
from app.models.rbac import Permission, Role
from app.models.user import User, TherapistDocument
from app.repositories.base import BaseRepository
from app.schemas.user import (
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
    TherapistDocumentCreate,
)
from app.services.activity_service import activity_service
from app.services.email_service import email_service
from app.utils.slugify import unique_slug

router = APIRouter(prefix="/users", tags=["Users & Roles"])

_users: BaseRepository[User] = BaseRepository(User)
_users.search_fields = ("name", "email")
_roles: BaseRepository[Role] = BaseRepository(Role)
_permissions: BaseRepository[Permission] = BaseRepository(Permission)


# ---- Users ------------------------------------------------------------


@router.get("", summary="List users")
async def list_users(
    role: Optional[str] = Query(None, description="Filter users by role"),
    params: PaginationParams = Depends(pagination_params),
    _: ActorContext = Depends(require_permission("users", "view")),
) -> dict:
    """Paginated list of admin/staff users."""
    filters = {"role": role} if role else None
    items, total = await _users.paginate(
        page=params.page,
        page_size=params.page_size,
        search=params.search,
        sort_by=params.sort_by,
        sort_order=params.sort_direction,
        filters=filters,
    )
    return paginated_response(UserResponse, items, total, params)


@router.post("", status_code=201, summary="Create user")
async def create_user(
    payload: UserCreate,
    bg_tasks: BackgroundTasks,
    actor: ActorContext = Depends(require_permission("users", "create")),
) -> dict:
    """Create a new admin/staff user."""
    email = payload.email.lower().strip()
    if await _users.exists({"email": email}):
        raise ConflictException("A user with this email already exists")

    plain_password = payload.password
    if not plain_password:
        # Generate a secure 12-character random password
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        plain_password = "".join(secrets.choice(alphabet) for _ in range(12))

    user_type = payload.user_type
    if payload.role.lower() == "therapist":
        user_type = "staff"

    user = User(
        name=payload.name,
        email=email,
        hashed_password=hash_password(plain_password),
        phone=payload.phone,
        role=payload.role,
        extra_permissions=payload.extra_permissions,
        user_type=user_type,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
    )
    await _users.create(user)

    if payload.send_credentials_email:
        bg_tasks.add_task(
            email_service.send_therapist_credentials_email,
            to=email,
            name=user.name,
            password=plain_password,
            role=user.role,
        )

    await activity_service.log(
        ActivityAction.CREATE, "users",
        user_id=actor.user_id, user_email=actor.email,
        entity_id=str(user.id), description=f"Created user {email}",
        ip_address=actor.ip_address, user_agent=actor.user_agent,
    )
    return item_response(UserResponse, user, "User created", )


@router.get("/{user_id}", summary="Get user")
async def get_user(
    user_id: str,
    _: ActorContext = Depends(require_permission("users", "view")),
) -> dict:
    user = await _users.get(user_id)
    if user is None:
        raise NotFoundException("User not found")
    return item_response(UserResponse, user)


@router.put("/{user_id}", summary="Update user")
async def update_user(
    user_id: str,
    payload: UserUpdate,
    actor: ActorContext = Depends(require_permission("users", "update")),
) -> dict:
    user = await _users.get(user_id)
    if user is None:
        raise NotFoundException("User not found")
    data = payload.model_dump(exclude_unset=True)
    await _users.update(user, data)
    await activity_service.log(
        ActivityAction.UPDATE, "users",
        user_id=actor.user_id, user_email=actor.email,
        entity_id=user_id, description=f"Updated user {user.email}",
        ip_address=actor.ip_address, user_agent=actor.user_agent,
    )
    return item_response(UserResponse, user, "User updated")


@router.delete("/{user_id}", summary="Delete user")
async def delete_user(
    user_id: str,
    actor: ActorContext = Depends(require_permission("users", "delete")),
) -> dict:
    if user_id == actor.user_id:
        raise ForbiddenException("You cannot delete your own account")
    user = await _users.get(user_id)
    if user is None:
        raise NotFoundException("User not found")
    await _users.delete(user)
    await activity_service.log(
        ActivityAction.DELETE, "users",
        user_id=actor.user_id, user_email=actor.email,
        entity_id=user_id, description=f"Deleted user {user.email}",
        ip_address=actor.ip_address, user_agent=actor.user_agent,
    )
    return success_response(message="User deleted")


# ---- Documents --------------------------------------------------------

@router.post("/me/documents", status_code=201, summary="Upload a document")
async def add_document(
    payload: TherapistDocumentCreate,
    actor: ActorContext = Depends(require_permission("profile", "update")),
) -> dict:
    """Upload a certificate or document to the user's profile."""
    user = await _users.get(actor.user_id)
    if user is None:
        raise NotFoundException("User not found")
    
    doc = TherapistDocument(
        title=payload.title,
        file=payload.file,
    )
    user.documents.append(doc)
    await _users.update(user, {"documents": user.documents})
    return success_response(data=doc.model_dump(mode="json"), message="Document added")


@router.delete("/me/documents/{doc_id}", summary="Delete a document")
async def delete_document(
    doc_id: str,
    actor: ActorContext = Depends(require_permission("profile", "update")),
) -> dict:
    """Delete a certificate or document from the user's profile."""
    user = await _users.get(actor.user_id)
    if user is None:
        raise NotFoundException("User not found")
    
    initial_count = len(user.documents)
    user.documents = [doc for doc in user.documents if doc.id != doc_id]
    
    if len(user.documents) == initial_count:
        raise NotFoundException("Document not found")
        
    await _users.update(user, {"documents": user.documents})
    return success_response(message="Document deleted")


@router.patch("/{user_id}/documents/{doc_id}/verify", summary="Verify a document")
async def verify_document(
    user_id: str,
    doc_id: str,
    actor: ActorContext = Depends(require_permission("users", "update")),
) -> dict:
    """Verify or unverify a therapist's document (Admin only)."""
    user = await _users.get(user_id)
    if user is None:
        raise NotFoundException("User not found")
    
    doc = next((d for d in user.documents if d.id == doc_id), None)
    if doc is None:
        raise NotFoundException("Document not found")
        
    from app.models.base import utcnow
    
    doc.is_verified = not doc.is_verified
    doc.verified_at = utcnow() if doc.is_verified else None
    
    await _users.update(user, {"documents": user.documents})
    return success_response(
        data=doc.model_dump(mode="json"),
        message=f"Document {'verified' if doc.is_verified else 'unverified'} successfully"
    )


# ---- Roles ------------------------------------------------------------


@router.get("/roles/all", summary="List roles")
async def list_roles(
    _: ActorContext = Depends(require_permission("roles", "view")),
) -> dict:
    roles = await _roles.list(sort=[("name", 1)])
    data = [RoleResponse.model_validate(r).model_dump(mode="json") for r in roles]
    return success_response(data=data, message="Roles fetched")


@router.post("/roles", status_code=201, summary="Create role")
async def create_role(
    payload: RoleCreate,
    actor: ActorContext = Depends(require_permission("roles", "create")),
) -> dict:
    slug = payload.slug or await unique_slug(
        payload.name, lambda s: _roles.exists({"slug": s})
    )
    if await _roles.exists({"slug": slug}):
        raise ConflictException("A role with this slug already exists")
    role = Role(
        slug=slug,
        name=payload.name,
        description=payload.description,
        permissions=payload.permissions,
    )
    await _roles.create(role)
    return item_response(RoleResponse, role, "Role created")


@router.put("/roles/{role_id}", summary="Update role")
async def update_role(
    role_id: str,
    payload: RoleUpdate,
    actor: ActorContext = Depends(require_permission("roles", "update")),
) -> dict:
    role = await _roles.get(role_id)
    if role is None:
        raise NotFoundException("Role not found")
    if role.is_system and payload.permissions is not None:
        raise ForbiddenException("System role permissions cannot be modified")
    await _roles.update(role, payload.model_dump(exclude_unset=True))
    return item_response(RoleResponse, role, "Role updated")


@router.delete("/roles/{role_id}", summary="Delete role")
async def delete_role(
    role_id: str,
    actor: ActorContext = Depends(require_permission("roles", "delete")),
) -> dict:
    role = await _roles.get(role_id)
    if role is None:
        raise NotFoundException("Role not found")
    if role.is_system:
        raise ForbiddenException("System roles cannot be deleted")
    await _roles.delete(role)
    return success_response(message="Role deleted")


# ---- Permissions ------------------------------------------------------


@router.get("/permissions/all", summary="List all permissions")
async def list_permissions(
    _: ActorContext = Depends(require_permission("roles", "view")),
) -> dict:
    """Return every permission code known to the system, grouped by resource."""
    perms = await _permissions.list(sort=[("group", 1), ("code", 1)])
    if perms:
        data = [PermissionResponse.model_validate(p).model_dump(mode="json") for p in perms]
    else:
        # Fall back to the static catalogue if the collection is empty.
        data = [{"code": c, "group": c.split(":")[0]} for c in all_permission_codes()]
    return success_response(data=data, message="Permissions fetched")
