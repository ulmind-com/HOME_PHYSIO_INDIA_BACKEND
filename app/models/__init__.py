"""Beanie document models.

``ALL_DOCUMENT_MODELS`` is consumed by the database initialiser to register
every collection with Beanie in a single place.
"""

from app.models.activity_log import ActivityLog
from app.models.blog import Blog, BlogCategory
from app.models.booking import Booking, Patient
from app.models.career import CareerJob, JobApplication, JobCategory
from app.models.contact import ContactMessage
from app.models.equipment import Equipment, EquipmentCategory, EquipmentRental
from app.models.faq import FAQ
from app.models.elder_care import ElderCareRequest
from app.models.infection_control import InfectionControlEnquiry, InfectionControlPageContent
from app.models.medical_report import MedicalReport
from app.models.notification import Notification
from app.models.pricing_settings import PricingSettings
from app.models.rbac import Permission, Role
from app.models.service import Category, Service
from app.models.settings import SEOSettings, SocialLinks, WebsiteSettings
from app.models.staff import StaffMember
from app.models.testimonial import Testimonial
from app.models.therapy_booking import TherapyBooking
from app.models.token import RefreshToken
from app.models.user import AdminSession, User
from app.models.user_type import UserType
from app.models.video import Video

ALL_DOCUMENT_MODELS = [
    User,
    AdminSession,
    RefreshToken,
    Role,
    Permission,
    UserType,
    Category,
    Service,
    Booking,
    Patient,
    TherapyBooking,
    Equipment,
    EquipmentCategory,
    EquipmentRental,
    JobCategory,
    CareerJob,
    JobApplication,
    Blog,
    BlogCategory,
    Video,
    Testimonial,
    StaffMember,
    FAQ,
    ElderCareRequest,
    ContactMessage,
    WebsiteSettings,
    SEOSettings,
    SocialLinks,
    Notification,
    PricingSettings,
    ActivityLog,
    InfectionControlPageContent,
    InfectionControlEnquiry,
    MedicalReport,
]

__all__ = [
    "ALL_DOCUMENT_MODELS",
    "User",
    "AdminSession",
    "RefreshToken",
    "Role",
    "Permission",
    "UserType",
    "Category",
    "Service",
    "Booking",
    "Patient",
    "TherapyBooking",
    "Equipment",
    "EquipmentCategory",
    "EquipmentRental",
    "JobCategory",
    "CareerJob",
    "JobApplication",
    "Blog",
    "BlogCategory",
    "Video",
    "Testimonial",
    "StaffMember",
    "FAQ",
    "ContactMessage",
    "WebsiteSettings",
    "SEOSettings",
    "SocialLinks",
    "Notification",
    "PricingSettings",
    "ActivityLog",
    "InfectionControlPageContent",
    "InfectionControlEnquiry",
    "MedicalReport",
]
