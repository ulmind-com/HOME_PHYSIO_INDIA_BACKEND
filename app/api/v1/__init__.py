"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.blogs.router import router as blogs_router
from app.api.v1.bookings.router import router as bookings_router
from app.api.v1.careers.router import router as careers_router
from app.api.v1.contact.router import router as contact_router
from app.api.v1.dashboard.router import router as dashboard_router
from app.api.v1.equipment.router import router as equipment_router
from app.api.v1.faq.router import router as faq_router
from app.api.v1.infection_control.router import router as infection_control_router
from app.api.v1.notifications.router import router as notifications_router
from app.api.v1.reviews.router import router as reviews_router
from app.api.v1.search.router import router as search_router
from app.api.v1.services.router import router as services_router
from app.api.v1.settings.router import router as settings_router
from app.api.v1.staff.router import router as staff_router
from app.api.v1.testimonials.router import router as testimonials_router
from app.api.v1.uploads.router import router as uploads_router
from app.api.v1.users.router import router as users_router
from app.api.v1.user_types.router import router as user_types_router
from app.api.v1.videos.router import router as videos_router
from app.api.v1.medical_reports.router import router as medical_reports_router
from app.api.v1.therapists.router import router as therapists_router
from app.api.v1.therapy_bookings.router import router as therapy_bookings_router
from app.api.v1.video.router import router as video_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(user_types_router)
api_router.include_router(dashboard_router)
api_router.include_router(services_router)
api_router.include_router(bookings_router)
api_router.include_router(equipment_router)
api_router.include_router(careers_router)
api_router.include_router(blogs_router)
api_router.include_router(videos_router)
api_router.include_router(testimonials_router)
api_router.include_router(staff_router)
api_router.include_router(faq_router)
api_router.include_router(reviews_router)
api_router.include_router(contact_router)
api_router.include_router(settings_router)
api_router.include_router(infection_control_router)
api_router.include_router(medical_reports_router)
api_router.include_router(notifications_router)
api_router.include_router(uploads_router)
api_router.include_router(search_router)
api_router.include_router(therapists_router)
api_router.include_router(therapy_bookings_router)
api_router.include_router(video_router)


__all__ = ["api_router"]
