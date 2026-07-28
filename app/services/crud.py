"""Generic CRUD service used by content modules.

Encapsulates the create/read/update/delete workflow shared by services,
blogs, equipment, videos, testimonials, FAQs, careers, etc. — including slug
generation, activity logging and pagination — so each module's router stays a
thin, declarative layer (DRY + SRP).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, TypeVar

from beanie import Document

from app.core.exceptions import NotFoundException
from app.dependencies.auth import ActorContext
from app.models.enums import ActivityAction
from app.repositories.base import BaseRepository
from app.services.activity_service import activity_service
from app.utils.slugify import unique_slug

ModelT = TypeVar("ModelT", bound=Document)


class CrudService:
    """Reusable CRUD orchestration for a single document type."""

    def __init__(
        self,
        model: Type[ModelT],
        entity: str,
        search_fields: Sequence[str] = (),
        slug_source: Optional[str] = None,
    ) -> None:
        """Create a CRUD service.

        Args:
            model: The Beanie document type.
            entity: Logical entity name used in activity logs / errors.
            search_fields: Fields scanned by free-text search.
            slug_source: Field whose value seeds the auto-generated ``slug``.
        """
        self.model = model
        self.entity = entity
        self.slug_source = slug_source
        self.repo: BaseRepository = BaseRepository(model)
        self.repo.search_fields = search_fields

    async def _slug_taken(self, slug: str, exclude_id: Optional[str] = None) -> bool:
        existing = await self.repo.find_one({"slug": slug})
        if existing is None:
            return False
        return str(existing.id) != exclude_id if exclude_id else True

    async def get_or_404(self, doc_id: str) -> ModelT:
        """Return a document by id or raise 404."""
        doc = await self.repo.get(doc_id)
        if doc is None:
            raise NotFoundException(f"{self.entity.capitalize()} not found")
        return doc

    async def get_by_slug(self, slug: str) -> ModelT:
        """Return a document by slug or raise 404."""
        doc = await self.repo.find_one({"slug": slug})
        if doc is None:
            raise NotFoundException(f"{self.entity.capitalize()} not found")
        return doc

    async def create(self, data: Dict[str, Any], actor: ActorContext) -> ModelT:
        """Create a document, generating a slug when applicable."""
        if self.slug_source and not data.get("slug"):
            source = data.get(self.slug_source) or self.entity
            data["slug"] = await unique_slug(
                str(source), lambda s: self._slug_taken(s)
            )
        doc = self.model(**data)
        await self.repo.create(doc)
        await self._audit(ActivityAction.CREATE, doc, actor)
        return doc

    async def update(
        self, doc_id: str, data: Dict[str, Any], actor: ActorContext
    ) -> ModelT:
        """Update a document by id."""
        doc = await self.get_or_404(doc_id)
        if "slug" in data and data["slug"]:
            if await self._slug_taken(data["slug"], exclude_id=doc_id):
                data["slug"] = await unique_slug(
                    data["slug"], lambda s: self._slug_taken(s, exclude_id=doc_id)
                )
        await self.repo.update(doc, data)
        await self._audit(ActivityAction.UPDATE, doc, actor)
        return doc

    async def delete(self, doc_id: str, actor: ActorContext) -> None:
        """Delete a document by id."""
        doc = await self.get_or_404(doc_id)
        await self.repo.delete(doc)
        await self._audit(ActivityAction.DELETE, doc, actor)

    async def paginate(
        self,
        page: int,
        page_size: int,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: int = -1,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ModelT], int]:
        """Paginate documents with optional filters and search."""
        return await self.repo.paginate(
            filters=filters,
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def _audit(
        self, action: ActivityAction, doc: ModelT, actor: ActorContext
    ) -> None:
        await activity_service.log(
            action,
            self.entity,
            user_id=actor.user_id,
            user_email=actor.email,
            entity_id=str(doc.id),
            description=f"{action} {self.entity}",
            ip_address=actor.ip_address,
            user_agent=actor.user_agent,
        )
