"""Contact message document."""

from __future__ import annotations

from typing import Optional

import pymongo
from pydantic import EmailStr

from app.models.base import TimestampedDocument
from app.models.enums import ContactStatus


class ContactMessage(TimestampedDocument):
    """A message submitted through the public contact form."""

    name: str
    email: EmailStr
    phone: Optional[str] = None
    subject: Optional[str] = None
    message: str

    status: ContactStatus = ContactStatus.NEW
    admin_notes: Optional[str] = None
    ip_address: Optional[str] = None

    class Settings:
        name = "contact_messages"
        indexes = [
            [("status", pymongo.ASCENDING)],
            [("created_at", pymongo.DESCENDING)],
            [("name", pymongo.TEXT), ("email", pymongo.TEXT), ("subject", pymongo.TEXT)],
        ]
