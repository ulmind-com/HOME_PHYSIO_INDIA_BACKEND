"""Medical Reports API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.api.helpers import item_response, paginated_response
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.pagination import PaginationParams, pagination_params
from app.core.permissions import ALL
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, _resolve_permissions, get_current_active_user, require_permission
from app.models.booking import Booking
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


async def _therapist_assigned_patient_ids(user: User) -> set[str]:
    """Patient ids whose care is currently assigned to this therapist."""
    assigned_bookings = await Booking.find({"assigned_staff_id": str(user.id)}).to_list()
    patient_ids = {b.patient_id for b in assigned_bookings if b.patient_id}
    for b in assigned_bookings:
        if b.contact_email:
            patient_user = await User.find_one({"email": b.contact_email})
            if patient_user:
                patient_ids.add(str(patient_user.id))
    return patient_ids


async def _authorize_report_access(report: MedicalReport, user: User, action: str) -> None:
    """Enforce patient/therapist/staff scoping for a single-report operation.

    Mirrors the scoping ``list_reports`` already applies, so a therapist can
    never view/update/review/delete a report for a patient they aren't
    assigned to just by knowing/guessing the report id.
    """
    if user.user_type == "patient":
        if report.patient_id != str(user.id):
            raise ForbiddenException(f"You don't have access to {action} this report")
        return

    perms = await _resolve_permissions(user)
    required = f"medical_reports:{action}"
    if ALL not in perms and required not in perms and "medical_reports:*" not in perms:
        raise ForbiddenException(f"Missing required permission: {required}")

    if user.role == "therapist" and ALL not in perms:
        assigned_ids = await _therapist_assigned_patient_ids(user)
        if report.patient_id not in assigned_ids:
            raise ForbiddenException("You are not assigned to this patient")


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
    elif user.role == "therapist":
        # Therapists can only see reports of patients assigned to them
        assigned_patient_ids = await _therapist_assigned_patient_ids(user)

        if patient_id and patient_id in assigned_patient_ids:
            query["patient_id"] = patient_id
        elif not patient_id:
            query["patient_id"] = {"$in": list(assigned_patient_ids)} if assigned_patient_ids else "__none__"
        else:
            raise ForbiddenException("You are not assigned to this patient")
    else:
        # Require permission if not a patient
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
        filters=query
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
    else:
        perms = await _resolve_permissions(user)
        if ALL not in perms and "medical_reports:create" not in perms and "medical_reports:*" not in perms:
             raise ForbiddenException("Missing required permission: medical_reports:create")
        if user.role == "therapist" and ALL not in perms:
            assigned_ids = await _therapist_assigned_patient_ids(user)
            if patient_id not in assigned_ids:
                raise ForbiddenException("You are not assigned to this patient")

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

    await _authorize_report_access(report, user, "view")

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

    await _authorize_report_access(report, user, "update")

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

    if actor.user.role == "therapist":
        perms = await _resolve_permissions(actor.user)
        if ALL not in perms:
            assigned_ids = await _therapist_assigned_patient_ids(actor.user)
            if report.patient_id not in assigned_ids:
                raise ForbiddenException("You are not assigned to this patient")

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

    await _authorize_report_access(report, user, "delete")

    # Delete from Cloudinary
    if report.file and hasattr(report.file, "public_id") and report.file.public_id:
        resource_type = getattr(report.file, "resource_type", "image")
        if not resource_type: 
            resource_type = "image"
        await cloudinary_service.delete(report.file.public_id, resource_type=resource_type)

    await _reports.delete(report)
    return success_response(message="Report deleted successfully")
