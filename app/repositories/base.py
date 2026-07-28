"""Generic asynchronous repository for Beanie documents.

Encapsulates all Mongo access behind a typed, reusable interface so services
never touch the ODM directly (Dependency Inversion / SRP). Provides CRUD,
pagination, search, filtering, sorting and aggregation counting.
"""

from __future__ import annotations

from typing import Any, Dict, Generic, List, Optional, Sequence, Tuple, Type, TypeVar

from beanie import Document
from bson import ObjectId
from bson.errors import InvalidId

from app.models.base import TimestampedDocument

ModelT = TypeVar("ModelT", bound=Document)


class BaseRepository(Generic[ModelT]):
    """Reusable async data-access object for a single Beanie document type."""

    #: Fields scanned by :meth:`paginate` when a free-text ``search`` is given.
    search_fields: Sequence[str] = ()

    def __init__(self, model: Type[ModelT]) -> None:
        self.model = model

    # ---- Helpers -------------------------------------------------------

    @staticmethod
    def is_valid_id(value: str) -> bool:
        """Return ``True`` if ``value`` is a valid Mongo ObjectId string."""
        return ObjectId.is_valid(value)

    # ---- Create --------------------------------------------------------

    async def create(self, document: ModelT) -> ModelT:
        """Insert a new document."""
        return await document.insert()

    # ---- Read ----------------------------------------------------------

    async def get(self, doc_id: str) -> Optional[ModelT]:
        """Fetch a document by its string id, tolerating invalid ids."""
        try:
            return await self.model.get(ObjectId(doc_id))
        except (InvalidId, TypeError):
            return None

    async def find_one(self, filters: Dict[str, Any]) -> Optional[ModelT]:
        """Return the first document matching ``filters``."""
        return await self.model.find_one(filters)

    async def exists(self, filters: Dict[str, Any]) -> bool:
        """Return ``True`` if any document matches ``filters``."""
        return await self.model.find_one(filters) is not None

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Tuple[str, int]]] = None,
        limit: Optional[int] = None,
    ) -> List[ModelT]:
        """Return documents matching ``filters`` (no pagination envelope)."""
        query = self.model.find(filters or {})
        if sort:
            query = query.sort(sort)
        if limit:
            query = query.limit(limit)
        return await query.to_list()

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count documents matching ``filters``."""
        return await self.model.find(filters or {}).count()

    async def paginate(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: int = -1,
    ) -> Tuple[List[ModelT], int]:
        """Return a page of documents plus the total matching count.

        Combines caller-supplied ``filters`` with a case-insensitive regex
        ``search`` across :attr:`search_fields`.
        """
        query_filter: Dict[str, Any] = dict(filters or {})

        if search and self.search_fields:
            regex = {"$regex": search.strip(), "$options": "i"}
            query_filter = {
                "$and": [
                    query_filter,
                    {"$or": [{field: regex} for field in self.search_fields]},
                ]
            } if query_filter else {"$or": [{field: regex} for field in self.search_fields]}

        total = await self.model.find(query_filter).count()

        sort_field = sort_by or "created_at"
        query = (
            self.model.find(query_filter)
            .sort([(sort_field, sort_order)])
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        items = await query.to_list()
        return items, total

    # ---- Update --------------------------------------------------------

    async def update(self, document: ModelT, data: Dict[str, Any]) -> ModelT:
        """Apply ``data`` to ``document`` and persist, refreshing timestamps."""
        for key, value in data.items():
            setattr(document, key, value)
        if isinstance(document, TimestampedDocument):
            document.touch()
        await document.save()
        return document

    # ---- Delete --------------------------------------------------------

    async def delete(self, document: ModelT) -> None:
        """Hard-delete a document."""
        await document.delete()

    async def delete_by_id(self, doc_id: str) -> bool:
        """Delete by id; returns ``True`` if a document was removed."""
        document = await self.get(doc_id)
        if document is None:
            return False
        await document.delete()
        return True
