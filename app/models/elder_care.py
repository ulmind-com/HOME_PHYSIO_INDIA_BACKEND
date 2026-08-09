from typing import Optional
import pymongo
from app.models.base import TimestampedDocument

class ElderCareRequest(TimestampedDocument):
    """A request for elder care services submitted from the public website."""

    full_name: str
    phone_number: str
    city: str
    service_type: str
    
    # Optional legacy fields
    patient_condition: Optional[str] = None
    preferred_duty_hours: Optional[str] = None
    
    # Status of the request (e.g., pending, in_progress, completed, cancelled)
    status: str = "pending"

    class Settings:
        name = "elder_care_requests"
        indexes = [[("phone_number", pymongo.ASCENDING)], [("created_at", pymongo.DESCENDING)]]
