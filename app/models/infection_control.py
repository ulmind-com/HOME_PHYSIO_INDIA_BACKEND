"""Infection Control page content and enquiry models.

``InfectionControlPageContent`` is a singleton document storing all
editable content for the Infection Control Nurse Services page.

``InfectionControlEnquiry`` stores form submissions from the page.
"""

from __future__ import annotations

from typing import List, Optional

import pymongo
from pydantic import BaseModel, EmailStr, Field

from app.models.base import TimestampedDocument


class ICServiceItem(BaseModel):
    """A single service card on the Infection Control page."""

    title: str = ""
    description: str = ""
    order: int = 0


class ICWhyChooseItem(BaseModel):
    """A single 'Why Choose Us' card."""

    title: str = ""
    description: str = ""


class ICHowItWorksStep(BaseModel):
    """A single step in the 'How It Works' section."""

    step_label: str = ""
    title: str = ""
    description: str = ""


class ICFaqItem(BaseModel):
    """A single FAQ entry."""

    question: str = ""
    answer: str = ""


class InfectionControlPageContent(TimestampedDocument):
    """Singleton document holding all editable content for the
    Infection Control Nurse Services page."""

    # ── Hero section ─────────────────────────────────────
    hero_heading: str = "Infection Control Nurse Services"
    hero_subheading: str = "Professional Infection Prevention & Control Support for Healthcare Professionals and Care Settings"
    hero_short_text: str = "Get professional guidance and support in infection prevention and control practices, healthcare hygiene, staff training and infection-control protocols."
    hero_btn_primary: str = "Enquire Now"
    hero_btn_secondary: str = "Call Now"

    # ── Short Introduction ───────────────────────────────
    intro_heading: str = "Professional Infection Prevention & Control Support"
    intro_content: str = "Nupun Home Health Care Services provides professional infection prevention and control support for healthcare professionals, nursing teams, healthcare facilities and home-care environments. Our services focus on promoting safe practices, proper hygiene, infection prevention protocols and awareness in healthcare settings."

    # ── Our Comprehensive Services ───────────────────────
    services: List[ICServiceItem] = Field(default_factory=lambda: [
        ICServiceItem(title="Infection Prevention & Control", description="Support in implementing appropriate infection prevention and control practices.", order=0),
        ICServiceItem(title="Hand Hygiene & PPE Practices", description="Guidance on proper hand hygiene, personal protective equipment and safe healthcare practices.", order=1),
        ICServiceItem(title="Infection Control Training", description="Educational training and awareness sessions for healthcare staff and nursing professionals.", order=2),
        ICServiceItem(title="Infection Control Audit & Monitoring", description="Support with monitoring infection-control practices and identifying areas for improvement.", order=3),
        ICServiceItem(title="Biomedical Waste Management Guidance", description="Guidance regarding safe segregation, handling and disposal practices for biomedical waste.", order=4),
        ICServiceItem(title="Infection Surveillance & Documentation", description="Support with infection monitoring, documentation and maintaining appropriate records.", order=5),
        ICServiceItem(title="Infection Control Policies & Protocols", description="Guidance in developing and following appropriate infection-control policies and protocols.", order=6),
        ICServiceItem(title="Environmental Hygiene & Safety", description="Support for maintaining hygienic and safer healthcare environments.", order=7),
        ICServiceItem(title="Home Healthcare Infection Prevention", description="Infection-prevention guidance for home healthcare and patient-care environments.", order=8),
        ICServiceItem(title="Healthcare Staff Awareness & Education", description="Awareness and educational sessions covering essential infection-control practices.", order=9),
    ])

    # ── Why Choose Us ────────────────────────────────────
    why_choose_items: List[ICWhyChooseItem] = Field(default_factory=lambda: [
        ICWhyChooseItem(title="Professional Guidance", description="Focused support in infection prevention and control practices."),
        ICWhyChooseItem(title="Healthcare-Focused Approach", description="Our content and services are designed around practical healthcare environments."),
        ICWhyChooseItem(title="Training & Awareness", description="Promoting proper hygiene, PPE and infection-control practices among healthcare teams."),
        ICWhyChooseItem(title="Practical Support", description="Focus on implementing appropriate infection-control procedures in real-world settings."),
        ICWhyChooseItem(title="Patient Safety Focused", description="Helping healthcare environments maintain safer infection-prevention practices."),
    ])

    # ── How It Works ─────────────────────────────────────
    how_it_works_steps: List[ICHowItWorksStep] = Field(default_factory=lambda: [
        ICHowItWorksStep(step_label="Step 1", title="Submit Your Enquiry", description="Tell us about your requirement through the online enquiry form."),
        ICHowItWorksStep(step_label="Step 2", title="Requirement Discussion", description="Our team contacts you to understand your specific requirement."),
        ICHowItWorksStep(step_label="Step 3", title="Service Planning", description="The appropriate guidance, training or support requirement is discussed."),
        ICHowItWorksStep(step_label="Step 4", title="Support / Training", description="The agreed infection-control support or educational service is provided."),
        ICHowItWorksStep(step_label="Step 5", title="Follow-Up", description="Further guidance can be discussed according to the requirement."),
    ])

    # ── FAQ ──────────────────────────────────────────────
    faqs: List[ICFaqItem] = Field(default_factory=lambda: [
        ICFaqItem(question="What is an Infection Control Nurse?", answer="An Infection Control Nurse is a healthcare professional involved in infection prevention, monitoring, education and implementation of infection-control practices in healthcare settings."),
        ICFaqItem(question="Who can benefit from Infection Control Nurse services?", answer="Healthcare facilities, nursing teams, healthcare professionals and home-care environments can benefit from appropriate infection prevention and control support."),
        ICFaqItem(question="Do you provide Infection Control training?", answer="Training and educational support can be provided according to the specific requirement and scope of service."),
        ICFaqItem(question="Do you provide Infection Control support for home healthcare?", answer="Yes, infection-prevention guidance can be provided for appropriate home healthcare and patient-care environments."),
        ICFaqItem(question="What topics can be covered in Infection Control training?", answer="Topics may include hand hygiene, PPE, standard precautions, infection prevention practices, biomedical waste management and other relevant infection-control procedures."),
        ICFaqItem(question="Can nursing students enquire about Infection Control Nurse training?", answer="Yes. Nursing students and healthcare professionals can submit an enquiry regarding available educational or training support."),
        ICFaqItem(question="Do you provide an Infection Control Nurse certificate?", answer="Any certificate or training credential should be provided only according to the actual course, authorization, affiliation or recognition applicable to the program. Do not describe it as university/government recognized unless such recognition officially exists."),
        ICFaqItem(question="How can I enquire about Infection Control Nurse services?", answer="You can submit the enquiry form on this page or contact Nupun Home Health Care Services directly."),
    ])

    # ── Enquiry Section ──────────────────────────────────
    enquiry_heading: str = "Have an Infection Control Enquiry?"
    enquiry_subheading: str = "Tell us about your requirement and our team will contact you to discuss the appropriate Infection Prevention & Control support."
    enquiry_requirement_options: List[str] = Field(default_factory=lambda: [
        "Infection Control Training",
        "Infection Prevention & Control Support",
        "Healthcare Staff Training",
        "Infection Control Audit",
        "Home Healthcare Infection Prevention",
        "Student / Professional Enquiry",
        "Other",
    ])

    # ── Home Page Card ───────────────────────────────────
    home_card_title: str = "Infection Control Nurse Services"
    home_card_description: str = "Professional infection prevention and control support, training and guidance for healthcare professionals and care environments."
    home_card_button_text: str = "Learn More"

    is_active: bool = True

    class Settings:
        name = "infection_control_page_content"


class InfectionControlEnquiry(TimestampedDocument):
    """A public enquiry submitted from the Infection Control page."""

    full_name: str
    phone_number: str
    email: Optional[str] = None
    requirement_type: str = ""
    message: Optional[str] = None
    status: str = "pending"

    class Settings:
        name = "infection_control_enquiries"
        indexes = [
            [("phone_number", pymongo.ASCENDING)],
            [("created_at", pymongo.DESCENDING)],
        ]
