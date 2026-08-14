"""Careers endpoints: job categories, jobs and applications (with resume upload)."""

from __future__ import annotations

from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    Query,
    Request,
    Response,
    UploadFile,
)
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.api.helpers import item_response, paginated_response
from app.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.limiter import limiter
from app.core.pagination import PaginationParams, pagination_params
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.career import CareerJob, JobApplication, JobCategory
from app.models.enums import (
    ActivityAction,
    ApplicationStatus,
    ContentStatus,
    NotificationType,
)
from app.repositories.base import BaseRepository
from app.schemas.career import (
    ApplicationResponse,
    ApplicationStatusUpdate,
    JobCategoryCreate,
    JobCategoryResponse,
    JobCategoryUpdate,
    JobCreate,
    JobResponse,
    JobUpdate,
)
from app.services.activity_service import activity_service
from app.services.crud import CrudService
from app.services.email_service import email_service
from app.services.notification_service import notification_service
from app.services.cloudinary_service import cloudinary_service
from app.utils.files import MAX_FILE_BYTES, read_validated_document
from app.utils.references import generate_reference
from app.utils.sanitize import sanitize_str

router = APIRouter(prefix="/careers", tags=["Careers"])

_email_validator = TypeAdapter(EmailStr)

_job = CrudService(
    CareerJob, entity="careers", search_fields=("title", "description"),
    slug_source="title",
)
_category = CrudService(
    JobCategory, entity="categories", search_fields=("name",), slug_source="name",
)
_applications: BaseRepository[JobApplication] = BaseRepository(JobApplication)
_applications.search_fields = ("reference", "full_name", "email", "job_title")


# ---- Job categories ---------------------------------------------------


@router.get("/categories", summary="List job categories")
async def list_categories(active_only: bool = Query(True)) -> dict:
    filters = {"is_active": True} if active_only else None
    items = await _category.repo.list(filters=filters, sort=[("order", 1)])
    data = [JobCategoryResponse.model_validate(c).model_dump(mode="json") for c in items]
    return success_response(data=data, message="Categories fetched")


@router.post("/categories", status_code=201, summary="Create job category")
async def create_category(
    payload: JobCategoryCreate,
    actor: ActorContext = Depends(require_permission("careers", "create")),
) -> dict:
    doc = await _category.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(JobCategoryResponse, doc, "Category created")


@router.put("/categories/{category_id}", summary="Update job category")
async def update_category(
    category_id: str,
    payload: JobCategoryUpdate,
    actor: ActorContext = Depends(require_permission("careers", "update")),
) -> dict:
    doc = await _category.update(category_id, payload.model_dump(exclude_unset=True), actor)
    return item_response(JobCategoryResponse, doc, "Category updated")


@router.delete("/categories/{category_id}", summary="Delete job category")
async def delete_category(
    category_id: str,
    actor: ActorContext = Depends(require_permission("careers", "delete")),
) -> dict:
    await _category.delete(category_id, actor)
    return success_response(message="Category deleted")


# ---- Applications (declared before /{id}) -----------------------------


@router.post("/applications", status_code=201, summary="Apply to a job (public)")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def create_application(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    job_id: Optional[str] = Form(None, max_length=64),
    job_title: str = Form(..., min_length=1, max_length=200),
    full_name: str = Form(..., min_length=1, max_length=120),
    email: str = Form(..., max_length=254),
    phone: str = Form(..., min_length=3, max_length=30),
    experience: Optional[str] = Form(None, max_length=100),
    preferred_location: Optional[str] = Form(None, max_length=200),
    qualification: Optional[str] = Form(None, max_length=200),
    preferred_duty: Optional[str] = Form(None, max_length=100),
    previous_employer: Optional[str] = Form(None, max_length=200),
    relevant_skills: Optional[str] = Form(None, max_length=2000),
    certificates: Optional[str] = Form(None, max_length=1000),
    cover_letter: Optional[str] = Form(None, max_length=5000),
    resume: Optional[UploadFile] = None,
) -> dict:
    """Public endpoint: submit a job application with an optional resume file.

    Hardened against abuse: IP rate-limited, all free-text fields are sanitised
    (blocking stored-XSS), the email is format-validated, and the resume is
    checked by extension, MIME type, size and real file signature.
    """
    try:
        email = _email_validator.validate_python(email.strip())
    except ValidationError:
        raise BadRequestException("A valid email address is required")

    resume_asset = None
    if resume is not None:
        contents = await read_validated_document(resume, MAX_FILE_BYTES)
        file_asset = await cloudinary_service.upload_file(
            contents,
            folder="nupun/resumes",
            resource_type="auto",
            original_filename=resume.filename,
        )
        resume_asset = file_asset.model_dump()

    application = JobApplication(
        reference=generate_reference("NHA"),
        job_id=sanitize_str(job_id),
        job_title=sanitize_str(job_title),
        full_name=sanitize_str(full_name),
        email=email,
        phone=sanitize_str(phone),
        experience=sanitize_str(experience),
        preferred_location=sanitize_str(preferred_location),
        qualification=sanitize_str(qualification),
        preferred_duty=sanitize_str(preferred_duty),
        previous_employer=sanitize_str(previous_employer),
        relevant_skills=sanitize_str(relevant_skills),
        certificates=sanitize_str(certificates),
        cover_letter=sanitize_str(cover_letter, collapse_whitespace=False),
        resume=resume_asset,
    )
    await _applications.create(application)

    await notification_service.create(
        title="New job application",
        message=f"{full_name} applied for {job_title}",
        type=NotificationType.APPLICATION,
        reference_id=str(application.id),
    )
    background_tasks.add_task(
        email_service.send_application_confirmation,
        email,
        {"name": full_name, "job": job_title, "reference": application.reference},
    )
    return item_response(ApplicationResponse, application, "Application submitted")


@router.get("/applications", summary="List applications")
async def list_applications(
    params: PaginationParams = Depends(pagination_params),
    status: Optional[ApplicationStatus] = Query(None),
    job_id: Optional[str] = Query(None),
    _: ActorContext = Depends(require_permission("applications", "view")),
) -> dict:
    filters: dict = {}
    if status:
        filters["status"] = status
    if job_id:
        filters["job_id"] = job_id
    items, total = await _applications.paginate(
        filters=filters or None, page=params.page, page_size=params.page_size,
        search=params.search, sort_by=params.sort_by or "created_at",
        sort_order=params.sort_direction,
    )
    return paginated_response(ApplicationResponse, items, total, params)


@router.get("/applications/{application_id}", summary="Get application")
async def get_application(
    application_id: str,
    _: ActorContext = Depends(require_permission("applications", "view")),
) -> dict:
    app_doc = await _applications.get(application_id)
    if app_doc is None:
        raise NotFoundException("Application not found")
    return item_response(ApplicationResponse, app_doc)


@router.put("/applications/{application_id}", summary="Update application status")
async def update_application(
    application_id: str,
    payload: ApplicationStatusUpdate,
    actor: ActorContext = Depends(require_permission("applications", "update")),
) -> dict:
    app_doc = await _applications.get(application_id)
    if app_doc is None:
        raise NotFoundException("Application not found")
    await _applications.update(app_doc, payload.model_dump(exclude_unset=True))
    await activity_service.log(
        ActivityAction.UPDATE, "applications", user_id=actor.user_id,
        user_email=actor.email, entity_id=application_id,
        description=f"Application {payload.status}",
        ip_address=actor.ip_address, user_agent=actor.user_agent,
    )
    return item_response(ApplicationResponse, app_doc, "Application updated")


@router.delete("/applications/{application_id}", summary="Delete application")
async def delete_application(
    application_id: str,
    actor: ActorContext = Depends(require_permission("applications", "delete")),
) -> dict:
    deleted = await _applications.delete_by_id(application_id)
    if not deleted:
        raise NotFoundException("Application not found")
    return success_response(message="Application deleted")


# ---- Jobs -------------------------------------------------------------


@router.get("", summary="List jobs")
async def list_jobs(
    params: PaginationParams = Depends(pagination_params),
    status: Optional[ContentStatus] = Query(None),
    category_id: Optional[str] = Query(None),
) -> dict:
    filters: dict = {}
    if status:
        filters["status"] = status
    if category_id:
        filters["category_id"] = category_id
    items, total = await _job.paginate(
        page=params.page, page_size=params.page_size, search=params.search,
        sort_by=params.sort_by or "order", sort_order=params.sort_direction,
        filters=filters or None,
    )
    return paginated_response(JobResponse, items, total, params)


@router.get("/slug/{slug}", summary="Get job by slug")
async def get_job_by_slug(slug: str) -> dict:
    doc = await _job.get_by_slug(slug)
    return item_response(JobResponse, doc)


@router.get("/{job_id}", summary="Get job by id")
async def get_job(job_id: str) -> dict:
    doc = await _job.get_or_404(job_id)
    return item_response(JobResponse, doc)


@router.post("", status_code=201, summary="Create job")
async def create_job(
    payload: JobCreate,
    actor: ActorContext = Depends(require_permission("careers", "create")),
) -> dict:
    doc = await _job.create(payload.model_dump(exclude_unset=True), actor)
    return item_response(JobResponse, doc, "Job created")


@router.put("/{job_id}", summary="Update job")
async def update_job(
    job_id: str,
    payload: JobUpdate,
    actor: ActorContext = Depends(require_permission("careers", "update")),
) -> dict:
    doc = await _job.update(job_id, payload.model_dump(exclude_unset=True), actor)
    return item_response(JobResponse, doc, "Job updated")


@router.delete("/{job_id}", summary="Delete job")
async def delete_job(
    job_id: str,
    actor: ActorContext = Depends(require_permission("careers", "delete")),
) -> dict:
    await _job.delete(job_id, actor)
    return success_response(message="Job deleted")
