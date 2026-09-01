"""Medical Reports API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.api.helpers import item_response, paginated_response
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, get_current_active_user, require_permission
from app.models.medical_report import MedicalReport, ReportStatus, ReportType
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.medical_report import MedicalReportResponse, MedicalReportReview
from app.services.cloudinary_service import cloudinary_service
from app.utils.files import (
    read_validated_image,
    read_validated_upload,
    IMAGE_TYPES,
    DOC_TYPES,
    MAX_IMAGE_BYTES,
    MAX_FILE_BYTES,
)

router = APIRouter(prefix="/medical-reports", tags=["Medical Reports"])
_reports: BaseRepository[MedicalReport] = BaseRepository(MedicalReport)
_reports.search_fields = ("title",)


@router.get("", summary="List medical reports")
async def list_reports(
    params: PaginationParams = Depends(pagination_params),
    patient_id: Optional[str] = None,
    user: User = Depends(get_current_active_user),
) -> dict:
    """List paginated medical reports. Patients see only theirs. Staff see all."""
    query = {}
    
    if user.user_type == "patient":
        query["patient_id"] = str(user.id)
    else:
        # Require permission if not a patient
        from app.dependencies.auth import _resolve_permissions
        from app.core.permissions import ALL
        perms = await _resolve_permissions(user)
        if ALL not in perms and "medical_reports:view" not in perms and "medical_reports:*" not in perms:
             raise ForbiddenException("Missing required permission: medical_reports:view")
             
        if patient_id:
            query["patient_id"] = patient_id

    items, total = await _reports.paginate(
        page=params.page,
        page_size=params.page_size,
        search=params.search,
        sort_by=params.sort_by,
        sort_order=params.sort_direction,
        query=query
    )
    return paginated_response(MedicalReportResponse, items, total, params)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Upload a medical report")
async def create_report(
    title: str = Form(..., min_length=2, max_length=150),
    report_type: ReportType = Form(...),
    patient_id: str = Form(""),
    file: UploadFile = File(...),
    user: User = Depends(get_current_active_user),
) -> dict:
    """Upload a new medical report."""
    # For patients, auto-set patient_id to their own ID
    if user.user_type == "patient":
        patient_id = str(user.id)
    elif not patient_id:
        raise BadRequestException("patient_id is required for non-patient uploads")
    elif user.user_type != "patient":
        from app.dependencies.auth import _resolve_permissions
        from app.core.permissions import ALL
        perms = await _resolve_permissions(user)
        if ALL not in perms and "medical_reports:create" not in perms and "medical_reports:*" not in perms:
             raise ForbiddenException("Missing required permission: medical_reports:create")

    # Validate file type and size
    is_image = file.content_type and file.content_type.startswith("image/")
    if is_image:
        file_bytes = await read_validated_upload(file, IMAGE_TYPES, MAX_IMAGE_BYTES)
    else:
        file_bytes = await read_validated_upload(file, IMAGE_TYPES | DOC_TYPES, MAX_FILE_BYTES)

    if is_image:
        asset = await cloudinary_service.upload_image(file_bytes, folder="home_physio_india/medical_reports")
    else:
        asset = await cloudinary_service.upload_file(file_bytes, folder="home_physio_india/medical_reports", original_filename=file.filename)

    report = MedicalReport(
        patient_id=patient_id,
        title=title,
        report_type=report_type,
        file=asset,
    )
    await _reports.create(report)
    return item_response(MedicalReportResponse, report, "Report uploaded successfully")


@router.get("/{report_id}", summary="Get a medical report")
async def get_report(
    report_id: str,
    user: User = Depends(get_current_active_user),
) -> dict:
    """Get a specific medical report."""
    report = await _reports.get(report_id)
    if not report:
        raise NotFoundException("Report not found")
        
    if user.user_type == "patient" and report.patient_id != str(user.id):
        raise ForbiddenException("You don't have access to this report")
        
    if user.user_type != "patient":
        from app.dependencies.auth import _resolve_permissions
        from app.core.permissions import ALL
        perms = await _resolve_permissions(user)
        if ALL not in perms and "medical_reports:view" not in perms and "medical_reports:*" not in perms:
             raise ForbiddenException("Missing required permission: medical_reports:view")

    return item_response(MedicalReportResponse, report)


@router.put("/{report_id}", summary="Update a medical report")
async def update_report(
    report_id: str,
    title: Optional[str] = Form(None, min_length=2, max_length=150),
    report_type: Optional[ReportType] = Form(None),
    file: Optional[UploadFile] = File(None),
    user: User = Depends(get_current_active_user),
) -> dict:
    """Update report metadata or replace the file."""
    report = await _reports.get(report_id)
    if not report:
        raise NotFoundException("Report not found")

    if user.user_type == "patient" and report.patient_id != str(user.id):
        raise ForbiddenException("You don't have access to update this report")
        
    if user.user_type != "patient":
        from app.dependencies.auth import _resolve_permissions
        from app.core.permissions import ALL
        perms = await _resolve_permissions(user)
        if ALL not in perms and "medical_reports:update" not in perms and "medical_reports:*" not in perms:
             raise ForbiddenException("Missing required permission: medical_reports:update")

    data = {}
    if title is not None:
        data["title"] = title
    if report_type is not None:
        data["report_type"] = report_type
        
    if file:
        file_bytes = await file.read()
        if file_bytes:
            # Delete old file
            if report.file and hasattr(report.file, "public_id") and report.file.public_id:
                resource_type = getattr(report.file, "resource_type", "image")
                if not resource_type: 
                    resource_type = "image"
                await cloudinary_service.delete(report.file.public_id, resource_type=resource_type)
            
            # Upload new file
            is_image = file.content_type and file.content_type.startswith("image/")
            if is_image:
                asset = await cloudinary_service.upload_image(file_bytes, folder="home_physio_india/medical_reports")
            else:
                asset = await cloudinary_service.upload_file(file_bytes, folder="home_physio_india/medical_reports", original_filename=file.filename)
            data["file"] = asset
            data["status"] = ReportStatus.UPLOADED  # Reset status if file changes

    await _reports.update(report, data)
    return item_response(MedicalReportResponse, report, "Report updated successfully")


@router.patch("/{report_id}/review", summary="Review a report")
async def review_report(
    report_id: str,
    payload: MedicalReportReview,
    actor: ActorContext = Depends(require_permission("medical_reports", "update")),
) -> dict:
    """Physio/Admin updates report status and adds notes."""
    report = await _reports.get(report_id)
    if not report:
        raise NotFoundException("Report not found")

    data = payload.model_dump(exclude_unset=True)
    data["reviewed_by_id"] = actor.user_id
    
    await _reports.update(report, data)
    return item_response(MedicalReportResponse, report, "Report reviewed successfully")


@router.delete("/{report_id}", summary="Delete a report")
async def delete_report(
    report_id: str,
    user: User = Depends(get_current_active_user),
) -> dict:
    """Delete a medical report and its file from Cloudinary."""
    report = await _reports.get(report_id)
    if not report:
        raise NotFoundException("Report not found")

    if user.user_type == "patient" and report.patient_id != str(user.id):
        raise ForbiddenException("You don't have access to delete this report")
        
    if user.user_type != "patient":
        from app.dependencies.auth import _resolve_permissions
        from app.core.permissions import ALL
        perms = await _resolve_permissions(user)
        if ALL not in perms and "medical_reports:delete" not in perms and "medical_reports:*" not in perms:
             raise ForbiddenException("Missing required permission: medical_reports:delete")

    # Delete from Cloudinary
    if report.file and hasattr(report.file, "public_id") and report.file.public_id:
        resource_type = getattr(report.file, "resource_type", "image")
        if not resource_type: 
            resource_type = "image"
        await cloudinary_service.delete(report.file.public_id, resource_type=resource_type)

    await _reports.delete(report)
    return success_response(message="Report deleted successfully")
