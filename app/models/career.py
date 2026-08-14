"""Careers documents: job categories, postings and applications."""

from __future__ import annotations

from typing import List, Optional

import pymongo
from beanie import Indexed
from pydantic import EmailStr, Field

from app.models.base import FileAsset, SEOMeta, TimestampedDocument
from app.models.enums import ApplicationStatus, ContentStatus, JobType


class JobCategory(TimestampedDocument):
    """A category grouping job postings (e.g. Nursing, Physiotherapy)."""

    name: str
    slug: Indexed(str, unique=True)  # type: ignore[valid-type]
    description: str = ""
    is_active: bool = True
    order: int = 0

    class Settings:
        name = "job_categories"
        indexes = [[("slug", pymongo.ASCENDING)]]


class CareerJob(TimestampedDocument):
    """A career / job posting."""

    title: str
    slug: Indexed(str, unique=True)  # type: ignore[valid-type]
    category_id: Optional[str] = None
    category_name: Optional[str] = None

    description: str = ""
    responsibilities: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)

    location: Optional[str] = None
    job_type: JobType = JobType.FULL_TIME
    experience: Optional[str] = None
    salary_range: Optional[str] = None
    vacancies: int = 1

    seo: SEOMeta = Field(default_factory=SEOMeta)

    is_featured: bool = False
    order: int = 0
    status: ContentStatus = ContentStatus.PUBLISHED

    class Settings:
        name = "career_jobs"
        indexes = [
            [("slug", pymongo.ASCENDING)],
            [("category_id", pymongo.ASCENDING)],
            [("status", pymongo.ASCENDING)],
            [("title", pymongo.TEXT), ("description", pymongo.TEXT)],
        ]


class JobApplication(TimestampedDocument):
    """A candidate's application to a job posting."""

    reference: Indexed(str, unique=True)  # type: ignore[valid-type]

    job_id: Optional[str] = None
    job_title: str

    full_name: str
    email: EmailStr
    phone: str
    experience: Optional[str] = None
    preferred_location: Optional[str] = None
    qualification: Optional[str] = None
    preferred_duty: Optional[str] = None
    previous_employer: Optional[str] = None
    relevant_skills: Optional[str] = None
    certificates: Optional[str] = None
    cover_letter: Optional[str] = None
    resume: Optional[FileAsset] = None

    status: ApplicationStatus = ApplicationStatus.RECEIVED
    admin_notes: Optional[str] = None

    class Settings:
        name = "job_applications"
        indexes = [
            [("reference", pymongo.ASCENDING)],
            [("job_id", pymongo.ASCENDING)],
            [("status", pymongo.ASCENDING)],
            [("created_at", pymongo.DESCENDING)],
            [("full_name", pymongo.TEXT), ("email", pymongo.TEXT)],
        ]
