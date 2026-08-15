"""Cloudinary upload endpoints: image, file, video, delete."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.enums import ActivityAction
from app.services.activity_service import activity_service
from app.services.cloudinary_service import cloudinary_service
from app.utils.files import (
    DOC_TYPES,
    IMAGE_TYPES,
    MAX_FILE_BYTES,
    MAX_IMAGE_BYTES,
    MAX_VIDEO_BYTES,
    VIDEO_TYPES,
    read_validated_upload,
    read_validated_image,
)

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("/image", summary="Upload an image")
async def upload_image(
    file: UploadFile = File(...),
    folder: str = Form("nupun/images"),
    actor: ActorContext = Depends(require_permission("media", "create")),
) -> dict:
    contents = await read_validated_image(file, MAX_IMAGE_BYTES)
    asset = await cloudinary_service.upload_image(contents, folder=folder)
    await activity_service.log(
        ActivityAction.UPLOAD, "media", user_id=actor.user_id,
        user_email=actor.email, description=f"Uploaded image to {folder}",
        ip_address=actor.ip_address, user_agent=actor.user_agent,
    )
    return success_response(data=asset.model_dump(), message="Image uploaded")


@router.post("/file", summary="Upload a document/file")
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Form("nupun/files"),
    actor: ActorContext = Depends(require_permission("media", "create")),
) -> dict:
    contents = await read_validated_upload(file, DOC_TYPES, MAX_FILE_BYTES)
    asset = await cloudinary_service.upload_file(
        contents, folder=folder, resource_type="auto",
        original_filename=file.filename,
    )
    return success_response(data=asset.model_dump(), message="File uploaded")


@router.post("/video", summary="Upload a video")
async def upload_video(
    file: UploadFile = File(...),
    folder: str = Form("nupun/videos"),
    actor: ActorContext = Depends(require_permission("media", "create")),
) -> dict:
    contents = await read_validated_upload(file, VIDEO_TYPES, MAX_VIDEO_BYTES)
    asset = await cloudinary_service.upload_file(
        contents, folder=folder, resource_type="video",
        original_filename=file.filename,
    )
    return success_response(data=asset.model_dump(), message="Video uploaded")


@router.delete("", summary="Delete an uploaded asset by public_id")
async def delete_asset(
    public_id: str = Query(..., description="Cloudinary public_id"),
    resource_type: str = Query("image", pattern="^(image|video|raw)$"),
    actor: ActorContext = Depends(require_permission("media", "delete")),
) -> dict:
    ok = await cloudinary_service.delete(public_id, resource_type=resource_type)
    await activity_service.log(
        ActivityAction.DELETE, "media", user_id=actor.user_id,
        user_email=actor.email, description=f"Deleted asset {public_id}",
        ip_address=actor.ip_address, user_agent=actor.user_agent,
    )
    return success_response(
        data={"deleted": ok}, message="Asset deleted" if ok else "Asset not found"
    )
