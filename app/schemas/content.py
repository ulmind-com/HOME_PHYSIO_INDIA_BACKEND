"""Schemas for videos, testimonials, FAQs and contact messages."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.base import FileAsset, ImageAsset
from app.models.enums import ContactStatus, VideoSource
from app.schemas.common import IdTimestampSchema


# ---- Video ----


class VideoCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    slug: Optional[str] = None
    description: str = ""
    category: Optional[str] = None
    source: VideoSource = VideoSource.YOUTUBE
    youtube_url: Optional[str] = None
    video_file: Optional[FileAsset] = None
    thumbnail: Optional[ImageAsset] = None
    is_featured: bool = False
    order: int = 0
    is_active: bool = True


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    source: Optional[VideoSource] = None
    youtube_url: Optional[str] = None
    video_file: Optional[FileAsset] = None
    thumbnail: Optional[ImageAsset] = None
    is_featured: Optional[bool] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class VideoResponse(IdTimestampSchema):
    title: str
    slug: str
    description: str
    category: Optional[str] = None
    source: VideoSource
    youtube_url: Optional[str] = None
    video_file: Optional[FileAsset] = None
    thumbnail: Optional[ImageAsset] = None
    is_featured: bool
    order: int
    is_active: bool


# ---- Testimonial ----


class TestimonialCreate(BaseModel):
    patient_name: str = Field(..., min_length=2, max_length=120)
    designation: Optional[str] = None
    photo: Optional[ImageAsset] = None
    message: str = Field(..., min_length=2)
    rating: int = Field(5, ge=1, le=5)
    is_featured: bool = False
    order: int = 0
    is_active: bool = True


class TestimonialUpdate(BaseModel):
    patient_name: Optional[str] = None
    designation: Optional[str] = None
    photo: Optional[ImageAsset] = None
    message: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    is_featured: Optional[bool] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class TestimonialResponse(IdTimestampSchema):
    patient_name: str
    designation: Optional[str] = None
    photo: Optional[ImageAsset] = None
    message: str
    rating: int
    is_featured: bool
    order: int
    is_active: bool


# ---- FAQ ----


class FAQCreate(BaseModel):
    question: str = Field(..., min_length=2)
    answer: str = Field(..., min_length=1)
    category: Optional[str] = None
    order: int = 0
    is_active: bool = True


class FAQUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class FAQResponse(IdTimestampSchema):
    question: str
    answer: str
    category: Optional[str] = None
    order: int
    is_active: bool


# ---- Contact ----


class ContactCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120, pattern=r"^[^<>]+$")
    phone: str = Field(..., max_length=20, pattern=r"^\+?[0-9\-\s\(\)]+$")
    email: Optional[EmailStr] = None
    service_required: Optional[str] = Field(None, max_length=100, pattern=r"^[^<>]*$")
    patient_location: Optional[str] = Field(None, max_length=200, pattern=r"^[^<>]*$")
    message: str = Field(..., min_length=2, max_length=5000, pattern=r"^[^<>]+$")


class ContactStatusUpdate(BaseModel):
    status: ContactStatus
    admin_notes: Optional[str] = None


class ContactResponse(IdTimestampSchema):
    name: str
    phone: str
    email: Optional[EmailStr] = None
    service_required: Optional[str] = None
    patient_location: Optional[str] = None
    message: str
    status: ContactStatus
    admin_notes: Optional[str] = None
