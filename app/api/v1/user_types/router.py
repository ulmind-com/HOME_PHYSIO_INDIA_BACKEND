"""User Types API routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, status
from slugify import slugify

from app.api.helpers import item_response
from app.core.exceptions import NotFoundException, BadRequestException
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.user_type import UserType
from app.schemas.user_type import UserTypeCreate, UserTypeUpdate, UserTypeResponse

router = APIRouter(prefix="/user-types", tags=["Users & Roles"])


@router.get("", summary="List all user types")
async def list_user_types() -> dict:
    """List all available user types."""
    user_types = await UserType.find_all().to_list()
    items = [UserTypeResponse.model_validate(ut).model_dump(mode="json") for ut in user_types]
    
    # Wrap in pagination format for frontend createCrudService compatibility
    data = {
        "items": items,
        "pagination": {
            "total": len(items),
            "page": 1,
            "page_size": max(len(items), 1)
        }
    }
    return success_response(data=data, message="User types fetched")


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create user type")
async def create_user_type(
    payload: UserTypeCreate,
    _: ActorContext = Depends(require_permission("roles", "create")),
) -> dict:
    """Create a new user type (Admin only)."""
    slug = payload.slug or slugify(payload.name)
    if await UserType.find_one({"slug": slug}) is not None:
        raise BadRequestException(f"User type with slug '{slug}' already exists")

    ut = UserType(
        name=payload.name,
        slug=slug,
        description=payload.description,
        is_core=payload.is_core,
    )
    await ut.insert()
    return item_response(UserTypeResponse, ut, "User type created")


from beanie import PydanticObjectId

async def _find_user_type(identifier: str) -> UserType | None:
    if PydanticObjectId.is_valid(identifier):
        ut = await UserType.get(identifier)
        if ut is not None:
            return ut
    return await UserType.find_one({"slug": identifier})


@router.put("/{type_id_or_slug}", summary="Update user type")
async def update_user_type(
    type_id_or_slug: str,
    payload: UserTypeUpdate,
    _: ActorContext = Depends(require_permission("roles", "update")),
) -> dict:
    """Update an existing user type (Admin only). Cannot rename core types."""
    ut = await _find_user_type(type_id_or_slug)
    if ut is None:
        raise NotFoundException("User type not found")

    if payload.name is not None:
        if ut.is_core and ut.name != payload.name:
            raise BadRequestException("Cannot change the name of a core user type")
        ut.name = payload.name
    
    if payload.description is not None:
        ut.description = payload.description

    await ut.save()
    return item_response(UserTypeResponse, ut, "User type updated")


@router.delete("/{type_id_or_slug}", summary="Delete user type")
async def delete_user_type(
    type_id_or_slug: str,
    _: ActorContext = Depends(require_permission("roles", "delete")),
) -> dict:
    """Delete a user type. Core types cannot be deleted."""
    ut = await _find_user_type(type_id_or_slug)
    if ut is None:
        raise NotFoundException("User type not found")

    if ut.is_core:
        raise BadRequestException("Core user types cannot be deleted")

    from app.models.user import User
    users_with_type = await User.find({"user_type": ut.slug}).count()
    if users_with_type > 0:
        raise BadRequestException(f"Cannot delete user type. {users_with_type} users are assigned this type.")

    await ut.delete()
    return success_response(message="User type deleted successfully", data={})
