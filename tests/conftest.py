"""Pytest fixtures.

Uses an in-memory Mongo (``mongomock-motor``) so tests run without any network
access or a real Atlas cluster. Beanie is initialised against the mock and the
default roles/admin are seeded, then the FastAPI app is driven with httpx.
"""

from __future__ import annotations

import os

# Ensure required settings exist before app imports read them.
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-not-secret")
os.environ.setdefault("MONGODB_URL", "mongomock://localhost")
os.environ.setdefault("MONGODB_DB_NAME", "nupun_health_test")
os.environ.setdefault("CORS_ORIGINS", "*")
os.environ.setdefault("FIRST_ADMIN_EMAIL", "admin@test.com")
os.environ.setdefault("FIRST_ADMIN_PASSWORD", "Admin@12345")

import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.database.seed import run_seed
from app.main import app
from app.models import ALL_DOCUMENT_MODELS


@pytest_asyncio.fixture(scope="function")
async def db():
    """Initialise Beanie against an in-memory Mongo and seed defaults."""
    client = AsyncMongoMockClient()
    await init_beanie(
        database=client["nupun_health_test"], document_models=ALL_DOCUMENT_MODELS
    )
    await run_seed()
    yield client


@pytest_asyncio.fixture(scope="function")
async def client(db):
    """Provide an httpx client bound to the app (lifespan not triggered)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def auth_headers(client):
    """Return Authorization headers for the seeded super-admin."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Admin@12345"},
    )
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
