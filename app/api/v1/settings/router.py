"""Website settings, social links and SEO endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.helpers import item_response
from app.core.exceptions import NotFoundException
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, require_permission
from app.models.settings import SEOSettings, SocialLinks, WebsiteSettings
from app.repositories.base import BaseRepository
from app.schemas.settings import (
    SEOSettingsResponse,
    SEOSettingsUpsert,
    SocialLinksResponse,
    SocialLinksUpdate,
    WebsiteSettingsResponse,
    WebsiteSettingsUpdate,
)

router = APIRouter(prefix="/settings", tags=["Settings & SEO"])

_website: BaseRepository[WebsiteSettings] = BaseRepository(WebsiteSettings)
_social: BaseRepository[SocialLinks] = BaseRepository(SocialLinks)
_seo: BaseRepository[SEOSettings] = BaseRepository(SEOSettings)


async def _get_or_create_website() -> WebsiteSettings:
    doc = await _website.find_one({})
    if doc is None:
        doc = WebsiteSettings()
        await _website.create(doc)
    return doc


async def _get_or_create_social() -> SocialLinks:
    doc = await _social.find_one({})
    if doc is None:
        doc = SocialLinks()
        await _social.create(doc)
    return doc


# ---- Website settings (singleton) -------------------------------------


@router.get("", summary="Get website settings (public)")
async def get_website_settings() -> dict:
    doc = await _get_or_create_website()
    return item_response(WebsiteSettingsResponse, doc)


@router.put("", summary="Update website settings")
async def update_website_settings(
    payload: WebsiteSettingsUpdate,
    actor: ActorContext = Depends(require_permission("settings", "update")),
) -> dict:
    doc = await _get_or_create_website()
    await _website.update(doc, payload.model_dump(exclude_unset=True))
    return item_response(WebsiteSettingsResponse, doc, "Settings updated")


# ---- Social links (singleton) -----------------------------------------


@router.get("/social", summary="Get social links (public)")
async def get_social_links() -> dict:
    doc = await _get_or_create_social()
    return item_response(SocialLinksResponse, doc)


@router.put("/social", summary="Update social links")
async def update_social_links(
    payload: SocialLinksUpdate,
    actor: ActorContext = Depends(require_permission("settings", "update")),
) -> dict:
    doc = await _get_or_create_social()
    await _social.update(doc, payload.model_dump(exclude_unset=True))
    return item_response(SocialLinksResponse, doc, "Social links updated")


# ---- SEO settings (per page_key) --------------------------------------


@router.get("/seo", summary="Get SEO settings for a page (public)")
async def get_seo(page_key: str = Query("global")) -> dict:
    doc = await _seo.find_one({"page_key": page_key})
    if doc is None:
        doc = SEOSettings(page_key=page_key)
    return item_response(SEOSettingsResponse, doc)


@router.get("/seo/all", summary="List all SEO settings")
async def list_seo(
    _: ActorContext = Depends(require_permission("seo", "view")),
) -> dict:
    items = await _seo.list(sort=[("page_key", 1)])
    data = [SEOSettingsResponse.model_validate(s).model_dump(mode="json") for s in items]
    return success_response(data=data, message="SEO settings fetched")


@router.put("/seo", summary="Create or update SEO settings for a page")
async def upsert_seo(
    payload: SEOSettingsUpsert,
    actor: ActorContext = Depends(require_permission("seo", "update")),
) -> dict:
    doc = await _seo.find_one({"page_key": payload.page_key})
    if doc is None:
        doc = SEOSettings(**payload.model_dump())
        await _seo.create(doc)
        message = "SEO settings created"
    else:
        await _seo.update(doc, payload.model_dump(exclude={"page_key"}))
        message = "SEO settings updated"
    return item_response(SEOSettingsResponse, doc, message)
