"""MongoDB (Motor) connection lifecycle and Beanie initialisation."""

from __future__ import annotations

from typing import Optional

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings
from app.core.logging import get_logger
from app.models import ALL_DOCUMENT_MODELS

logger = get_logger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> AsyncIOMotorClient:
    """Create the Motor client and verify connectivity."""
    global _client, _database

    if _client is not None:
        return _client

    logger.info("Connecting to MongoDB", extra={"db": settings.MONGODB_DB_NAME})
    _client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=10_000,
        uuidRepresentation="standard",
    )
    _database = _client[settings.MONGODB_DB_NAME]

    # Fail fast if the cluster is unreachable / credentials are wrong.
    await _client.admin.command("ping")
    logger.info("MongoDB connection established")
    return _client


async def init_database() -> None:
    """Initialise Beanie with all document models (registers indexes)."""
    if _database is None:
        await connect_to_mongo()
    await init_beanie(database=_database, document_models=ALL_DOCUMENT_MODELS)
    logger.info(
        "Beanie initialised", extra={"models": len(ALL_DOCUMENT_MODELS)}
    )


async def close_mongo_connection() -> None:
    """Close the Motor client on shutdown."""
    global _client, _database
    if _client is not None:
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")


def get_client() -> AsyncIOMotorClient:
    """Return the active Motor client (raises if not connected)."""
    if _client is None:
        raise RuntimeError("MongoDB client is not initialised")
    return _client


def get_database() -> AsyncIOMotorDatabase:
    """Return the active database handle (raises if not connected)."""
    if _database is None:
        raise RuntimeError("MongoDB database is not initialised")
    return _database


async def ping() -> bool:
    """Return ``True`` when the database responds to a ping."""
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:  # noqa: BLE001 - health check must never raise
        return False
