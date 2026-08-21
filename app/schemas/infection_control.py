"""Infection Control page schemas for request/response validation."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.infection_control import (
    ICFaqItem,
    ICHowItWorksStep,
    ICServiceItem,
    ICWhyChooseItem,
)
from app.schemas.common import IdTimestampSchema


# ── Page Content ────────────────────────────────────────────────

class InfectionControlContentUpdate(BaseModel):
    """Partial update payload for the page content singleton."""

    hero_heading: Optional[str] = None
    hero_subheading: Optional[str] = None
    hero_short_text: Optional[str] = None
    hero_btn_primary: Optional[str] = None
    hero_btn_secondary: Optional[str] = None

    intro_heading: Optional[str] = None
    intro_content: Optional[str] = None

    services: Optional[List[ICServiceItem]] = None
    why_choose_items: Optional[List[ICWhyChooseItem]] = None
    how_it_works_steps: Optional[List[ICHowItWorksStep]] = None
    faqs: Optional[List[ICFaqItem]] = None

    enquiry_heading: Optional[str] = None
    enquiry_subheading: Optional[str] = None
    enquiry_requirement_options: Optional[List[str]] = None

    home_card_title: Optional[str] = None
    home_card_description: Optional[str] = None
    home_card_button_text: Optional[str] = None


class InfectionControlContentResponse(IdTimestampSchema):
    """Full response for the page content singleton."""

    hero_heading: str = ""
    hero_subheading: str = ""
    hero_short_text: str = ""
    hero_btn_primary: str = ""
    hero_btn_secondary: str = ""

    intro_heading: str = ""
    intro_content: str = ""

    services: List[ICServiceItem] = Field(default_factory=list)
    why_choose_items: List[ICWhyChooseItem] = Field(default_factory=list)
    how_it_works_steps: List[ICHowItWorksStep] = Field(default_factory=list)
    faqs: List[ICFaqItem] = Field(default_factory=list)

    enquiry_heading: str = ""
    enquiry_subheading: str = ""
    enquiry_requirement_options: List[str] = Field(default_factory=list)

    home_card_title: str = ""
    home_card_description: str = ""
    home_card_button_text: str = ""


# ── Enquiry ─────────────────────────────────────────────────────

class InfectionControlEnquiryCreate(BaseModel):
    """Public enquiry form submission."""

    full_name: str = Field(..., min_length=2)
    phone_number: str = Field(..., min_length=7)
    email: Optional[str] = None
    requirement_type: str = ""
    message: Optional[str] = None


class InfectionControlEnquiryResponse(IdTimestampSchema):
    """Response schema for an enquiry record."""

    full_name: str
    phone_number: str
    email: Optional[str] = None
    requirement_type: str = ""
    message: Optional[str] = None
    status: str = "pending"


class InfectionControlEnquiryStatusUpdate(BaseModel):
    """Payload for updating an enquiry's status."""

    status: str
