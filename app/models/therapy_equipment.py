"""Bookable therapy equipment / modalities.

Replaces the old hardcoded ``EquipmentCode`` catalogue so that:

* admin can add equipment per service category with its own price, and
* a therapist can register their *own* equipment (with their own charge),
  which patients then see while booking that specific therapist.

Both live in one collection, separated by ``owner_type``.
"""

from __future__ import annotations

from typing import Optional

import pymongo
from pydantic import BaseModel

from app.models.base import ImageAsset, TimestampedDocument
from app.models.enums import EquipmentOwner, ServiceCategory


class TherapyEquipment(TimestampedDocument):
    """A single piece of equipment a patient can add to a therapy booking."""

    name: str
    slug: str
    description: str = ""

    #: Which service this equipment belongs to — a massage booking only ever
    #: shows ``massage_therapy`` equipment, a yoga booking only yoga, etc.
    category: ServiceCategory

    #: Charge added to the booking total when selected (Rs., per session).
    charge: int = 0

    #: ``platform`` equipment is managed by admin and offered for every
    #: therapist of that category; ``therapist`` equipment belongs to one
    #: therapist and is only offered when booking that therapist.
    owner_type: EquipmentOwner = EquipmentOwner.PLATFORM
    therapist_id: Optional[str] = None
    therapist_name: Optional[str] = None

    image: Optional[ImageAsset] = None
    is_active: bool = True
    sort_order: int = 0

    class Settings:
        name = "therapy_equipment"
        indexes = [
            [("category", pymongo.ASCENDING), ("is_active", pymongo.ASCENDING)],
            [("owner_type", pymongo.ASCENDING), ("therapist_id", pymongo.ASCENDING)],
            [("slug", pymongo.ASCENDING)],
        ]


class BookedEquipment(BaseModel):
    """Immutable snapshot of one equipment item, embedded in a booking.

    Stored on the booking so a later price edit or a deleted equipment row
    never rewrites what the patient actually agreed to pay.
    """

    equipment_id: str
    name: str
    charge: int
    owner_type: str = EquipmentOwner.PLATFORM.value
