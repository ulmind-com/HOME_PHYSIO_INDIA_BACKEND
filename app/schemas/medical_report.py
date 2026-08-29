"""Schemas for Medical Reports."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.models.base import FileAsset, ImageAsset
from app.models.medical_report import ReportStatus, ReportType
from app.schemas.common import IdTimestampSchema


class MedicalReportCreate(BaseModel):
    """Payload for creating a report metadata (usually used with form data)."""
    title: str = Field(..., min_length=2, max_length=150)
    report_type: ReportType
    patient_id: str


class MedicalReportReview(BaseModel):
    """Payload for Physio/Admin to review a report."""
    status: Optional[ReportStatus] = None
    physio_notes: Optional[str] = None


class MedicalReportResponse(IdTimestampSchema):
    """Response representation."""
    patient_id: str
    title: str
    report_type: ReportType
    file: FileAsset | ImageAsset
    status: ReportStatus
    physio_notes: str
    reviewed_by_id: Optional[str] = None
