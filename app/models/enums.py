"""Enumerations shared across models and schemas."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """String enum whose members serialise as their value."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)


class ContentStatus(StrEnum):
    """Publication status for content entities (services, blogs, ...)."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ActiveStatus(StrEnum):
    """Simple active/inactive toggle."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class BookingStatus(StrEnum):
    """Lifecycle of a home-care booking."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RentalStatus(StrEnum):
    """Lifecycle of an equipment rental request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class ApplicationStatus(StrEnum):
    """Lifecycle of a job application."""

    RECEIVED = "received"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    HIRED = "hired"


class JobType(StrEnum):
    """Employment type for a career posting."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"


class ContactStatus(StrEnum):
    """Lifecycle of a contact-form message."""

    NEW = "new"
    READ = "read"
    REPLIED = "replied"
    CLOSED = "closed"


class Gender(StrEnum):
    """Patient gender."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class VideoSource(StrEnum):
    """Where a video is hosted."""

    YOUTUBE = "youtube"
    CLOUDINARY = "cloudinary"


class NotificationType(StrEnum):
    """Category of an admin notification."""

    BOOKING = "booking"
    CONTACT = "contact"
    APPLICATION = "application"
    RENTAL = "rental"
    ENQUIRY = "enquiry"
    SYSTEM = "system"


class TherapistQualification(StrEnum):
    """Recognised physiotherapy qualification for a therapist account."""

    MPT = "MPT"
    BPT = "BPT"
    PT = "PT"
    DPT = "DPT"


class TherapistTier(StrEnum):
    """Business tier assigned to a therapist by admin during approval."""

    VERIFIED = "verified"
    ASSOCIATE = "associate"
    PREMIUM = "premium"


class VerificationStatus(StrEnum):
    """Admin approval status for a therapist account."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ServiceCategory(StrEnum):
    """The 4 home-visit service categories offered on the platform."""

    PHYSIOTHERAPY = "physiotherapy"
    YOGA_THERAPY = "yoga_therapy"
    MASSAGE_THERAPY = "massage_therapy"
    HOME_REHABILITATION = "home_rehabilitation"


class FrequencyType(StrEnum):
    """How a physiotherapy/yoga/rehab visit is billed."""

    DAILY = "daily"
    WEEKLY = "weekly"
    PACKAGE = "package"


class Shift(StrEnum):
    """Broad time-of-day window the patient picks before a time slot."""

    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class EquipmentCode(StrEnum):
    """Portable equipment/modalities available for home-visit sessions."""

    IFT = "ift"
    TENS = "tens"
    UST = "ust"
    NMES = "nmes"
    FES = "fes"
    PORTABLE_EMS = "portable_ems"
    WAX_BATH = "wax_bath"
    HOT_COLD = "hot_cold"
    THERABAND = "theraband"


class MassageType(StrEnum):
    """Massage therapy pricing tiers."""

    NORMAL_OIL = "normal_oil"
    DRY = "dry"
    DEEP_TISSUE = "deep_tissue"


class PackageDuration(StrEnum):
    """Multi-visit package lengths."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class PaymentStatus(StrEnum):
    """Lifecycle of a Razorpay payment against a therapy booking."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class ActivityAction(StrEnum):
    """Admin action recorded in the activity log."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    APPROVE = "approve"
    REJECT = "reject"
    UPLOAD = "upload"
    EXPORT = "export"
