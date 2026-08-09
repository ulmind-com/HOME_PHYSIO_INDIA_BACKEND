from typing import Optional
import pymongo
from app.models.base import TimestampedDocument

class ElderCareRequest(TimestampedDocument):
    """A request for elder care services submitted from the public website."""

    full_name: str
    phone_number: str
    service_type: str
    patient_condition: str
    preferred_duty_hours: str
    
    # Status of the request (e.g., pending, in_progress, completed, cancelled)
    status: str = "pending"

    class Settings:
        name = "elder_care_requests"
        indexes = [[("phone_number", pymongo.ASCENDING)], [("created_at", pymongo.DESCENDING)]]
