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
    SYSTEM = "system"


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
