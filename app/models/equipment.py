"""Medical equipment catalogue and rental documents."""

from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

import pymongo
from beanie import Indexed
from pydantic import EmailStr, Field

from app.models.base import ImageAsset, SEOMeta, TimestampedDocument
from app.models.enums import ContentStatus, RentalStatus


class EquipmentCategory(TimestampedDocument):
    """A category grouping medical equipment."""

    name: str
    slug: Indexed(str, unique=True)  # type: ignore[valid-type]
    description: str = ""
    image: Optional[ImageAsset] = None
    order: int = 0
    is_active: bool = True

    class Settings:
        name = "equipment_categories"
        indexes = [[("slug", pymongo.ASCENDING)]]


class Equipment(TimestampedDocument):
    """A rentable / purchasable medical equipment item."""

    name: str
    slug: Indexed(str, unique=True)  # type: ignore[valid-type]
    short_description: str = ""
    description: str = ""

    category_id: Optional[str] = None
    category_name: Optional[str] = None

    featured_image: Optional[ImageAsset] = None
    gallery: List[ImageAsset] = Field(default_factory=list)

    # Pricing / rental.
    rental_price: Optional[float] = None
    rental_unit: str = "per day"  # per day / per week / per month
    security_deposit: Optional[float] = None
    min_rental_duration: Optional[int] = None
    max_rental_duration: Optional[int] = None

    specifications: Dict[str, str] = Field(default_factory=dict)

    stock: int = 0
    is_available: bool = True

    seo: SEOMeta = Field(default_factory=SEOMeta)

    is_featured: bool = False
    order: int = 0
    status: ContentStatus = ContentStatus.PUBLISHED

    class Settings:
        name = "equipment"
        indexes = [
            [("slug", pymongo.ASCENDING)],
            [("category_id", pymongo.ASCENDING)],
            [("status", pymongo.ASCENDING)],
            [("is_available", pymongo.ASCENDING)],
            [("name", pymongo.TEXT), ("short_description", pymongo.TEXT)],
        ]


class EquipmentRental(TimestampedDocument):
    """A rental request for a piece of equipment."""

    reference: Indexed(str, unique=True)  # type: ignore[valid-type]

    equipment_id: str
    equipment_name: str

    customer_name: str
    customer_phone: str
    customer_email: Optional[EmailStr] = None
    address: str

    start_date: dt.date
    end_date: Optional[dt.date] = None
    quantity: int = 1
    duration_days: Optional[int] = None

    total_amount: Optional[float] = None
    status: RentalStatus = RentalStatus.PENDING
    admin_notes: Optional[str] = None

    class Settings:
        name = "equipment_rentals"
        indexes = [
            [("reference", pymongo.ASCENDING)],
            [("equipment_id", pymongo.ASCENDING)],
            [("status", pymongo.ASCENDING)],
            [("created_at", pymongo.DESCENDING)],
        ]
