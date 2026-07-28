"""Careers schemas: job categories, jobs and applications."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.base import SEOMeta
from app.models.enums import ApplicationStatus, ContentStatus, JobType
from app.schemas.common import IdTimestampSchema


# ---- Job category ----


class JobCategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    slug: Optional[str] = None
    description: str = ""
    is_active: bool = True
    order: int = 0


class JobCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    order: Optional[int] = None


class JobCategoryResponse(IdTimestampSchema):
    name: str
    slug: str
    description: str
    is_active: bool
    order: int


# ---- Job ----


class JobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    slug: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    description: str = ""
    responsibilities: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    job_type: JobType = JobType.FULL_TIME
    experience: Optional[str] = None
    salary_range: Optional[str] = None
    vacancies: int = Field(1, ge=1)
    seo: SEOMeta = Field(default_factory=SEOMeta)
    is_featured: bool = False
    order: int = 0
    status: ContentStatus = ContentStatus.PUBLISHED


class JobUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    description: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    location: Optional[str] = None
    job_type: Optional[JobType] = None
    experience: Optional[str] = None
    salary_range: Optional[str] = None
    vacancies: Optional[int] = Field(None, ge=1)
    seo: Optional[SEOMeta] = None
    is_featured: Optional[bool] = None
    order: Optional[int] = None
    status: Optional[ContentStatus] = None


class JobResponse(IdTimestampSchema):
    title: str
    slug: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    description: str
    responsibilities: List[str]
    requirements: List[str]
    location: Optional[str] = None
    job_type: JobType
    experience: Optional[str] = None
    salary_range: Optional[str] = None
    vacancies: int
    seo: SEOMeta
    is_featured: bool
    order: int
    status: ContentStatus


# ---- Application ----


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    admin_notes: Optional[str] = None


class ApplicationResponse(IdTimestampSchema):
    reference: str
    job_id: Optional[str] = None
    job_title: str
    full_name: str
    email: EmailStr
    phone: str
    experience: Optional[str] = None
    cover_letter: Optional[str] = None
    resume: Optional[dict] = None
    status: ApplicationStatus
    admin_notes: Optional[str] = None
