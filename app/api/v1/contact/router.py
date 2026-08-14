"""Contact-form endpoints: public submission + admin management."""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response

from app.api.helpers import item_response, paginated_response
from app.config import settings
from app.core.exceptions import NotFoundException
from app.core.limiter import limiter
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.contact import ContactMessage
from app.models.enums import ActivityAction, ContactStatus, NotificationType
from app.repositories.base import BaseRepository
from app.schemas.content import ContactCreate, ContactResponse, ContactStatusUpdate
from app.services.activity_service import activity_service
from app.services.email_service import email_service
from app.services.notification_service import notification_service
from app.utils.sanitize import sanitize_str

router = APIRouter(prefix="/contact", tags=["Contact"])

_contacts: BaseRepository[ContactMessage] = BaseRepository(ContactMessage)
_contacts.search_fields = ("name", "email", "subject", "message")


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("", status_code=201, summary="Submit contact message (public)")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def create_contact(
    request: Request,
    response: Response,
    payload: ContactCreate,
    background_tasks: BackgroundTasks,
) -> dict:
    """Public endpoint: store a contact message and send confirmations."""
    message = ContactMessage(
        name=sanitize_str(payload.name),
        email=payload.email,
        phone=sanitize_str(payload.phone),
        service_required=sanitize_str(payload.service_required),
        patient_location=sanitize_str(payload.patient_location),
        message=sanitize_str(payload.message, collapse_whitespace=False),
        ip_address=_client_ip(request),
    )
    await _contacts.create(message)

    await notification_service.create(
        title="New contact message",
        message=f"{message.name}: {message.service_required or 'General Enquiry'}",
        type=NotificationType.CONTACT,
        reference_id=str(message.id),
    )
    # Confirmation to sender + notification to admin (non-blocking).
    if message.email:
        background_tasks.add_task(
            email_service.send_contact_confirmation,
            message.email,
            {"name": message.name, "message": message.message},
        )
    background_tasks.add_task(
        email_service.send_admin_notification,
        "New Contact Message",
        f"<p><b>{message.name}</b> (Phone: {message.phone}) wrote:</p>"
        f"<p>Service: {message.service_required or 'N/A'}<br/>Location: {message.patient_location or 'N/A'}</p>"
        f"<blockquote>{message.message}</blockquote>",
    )
    return item_response(ContactResponse, message, "Message sent successfully")


@router.get("", summary="List contact messages")
async def list_contacts(
    params: PaginationParams = Depends(pagination_params),
    status: Optional[ContactStatus] = Query(None),
    _: ActorContext = Depends(require_permission("contacts", "view")),
) -> dict:
    filters = {"status": status} if status else None
    items, total = await _contacts.paginate(
        filters=filters, page=params.page, page_size=params.page_size,
        search=params.search, sort_by=params.sort_by or "created_at",
        sort_order=params.sort_direction,
    )
    return paginated_response(ContactResponse, items, total, params)


@router.get("/{contact_id}", summary="Get contact message")
async def get_contact(
    contact_id: str,
    _: ActorContext = Depends(require_permission("contacts", "view")),
) -> dict:
    doc = await _contacts.get(contact_id)
    if doc is None:
        raise NotFoundException("Message not found")
    return item_response(ContactResponse, doc)


@router.put("/{contact_id}", summary="Update contact message status")
async def update_contact(
    contact_id: str,
    payload: ContactStatusUpdate,
    actor: ActorContext = Depends(require_permission("contacts", "update")),
) -> dict:
    doc = await _contacts.get(contact_id)
    if doc is None:
        raise NotFoundException("Message not found")
    await _contacts.update(doc, payload.model_dump(exclude_unset=True))
    await activity_service.log(
        ActivityAction.UPDATE, "contacts", user_id=actor.user_id,
        user_email=actor.email, entity_id=contact_id,
        description=f"Contact marked {payload.status}",
        ip_address=actor.ip_address, user_agent=actor.user_agent,
    )
    
    if payload.status != ContactStatus.NEW:
        await notification_service.mark_read_by_reference(contact_id)
    return item_response(ContactResponse, doc, "Message updated")


@router.delete("/{contact_id}", summary="Delete contact message")
async def delete_contact(
    contact_id: str,
    actor: ActorContext = Depends(require_permission("contacts", "delete")),
) -> dict:
    deleted = await _contacts.delete_by_id(contact_id)
    if not deleted:
        raise NotFoundException("Message not found")
    return success_response(message="Message deleted")
