"""Medical Reports document model."""

from __future__ import annotations

from enum import Enum
from typing import Optional

import pymongo
from beanie import Indexed
from pydantic import Field

from app.models.base import FileAsset, ImageAsset, TimestampedDocument


class ReportType(str, Enum):
    PRESCRIPTION = "Prescription"
    XRAY = "X-Ray"
    MRI = "MRI"
    MEDICAL_REPORT = "Medical Report"


class ReportStatus(str, Enum):
    UPLOADED = "Uploaded"
    VIEWED = "Viewed"
    REVIEWED = "Reviewed"


class MedicalReport(TimestampedDocument):
    """A medical report uploaded by a patient or on their behalf."""

    patient_id: Indexed(str)  # type: ignore[valid-type]
    title: str
    report_type: ReportType
    file: FileAsset | ImageAsset
    status: ReportStatus = ReportStatus.UPLOADED
    physio_notes: str = ""
    reviewed_by_id: Optional[str] = None

    class Settings:
        name = "medical_reports"
        indexes = [
            [("patient_id", pymongo.ASCENDING)],
            [("status", pymongo.ASCENDING)],
        ]
