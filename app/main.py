"""Application entrypoint: FastAPI app factory and lifecycle wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

import time
from app import __version__
from app.api.routers import elder_care
from app.api.v1 import api_router
from app.config import settings
from app.core.handlers import register_exception_handlers
from app.core.limiter import limiter
from app.core.logging import configure_logging, get_logger
from app.core.responses import success_response
from app.database.connection import (
    close_mongo_connection,
    connect_to_mongo,
    init_database,
    ping,
)
from app.database.seed import run_seed
from app.middleware import RequestContextMiddleware, SecurityHeadersMiddleware

logger = get_logger(__name__)

_DESCRIPTION = """
Backend API for **Home Physio India**.

A production-grade, API-only backend powering the admin panel and the public
website: services, bookings, medical equipment rentals, careers, blogs, videos,
testimonials, FAQs, contact, settings/SEO, uploads, notifications and more.

All responses follow a consistent envelope::

    { "success": true, "message": "", "data": {}, "errors": null }
"""


START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown: DB connect, Beanie init, seeding."""
    configure_logging(settings.DEBUG)
    logger.info("Starting application", extra={"env": settings.APP_ENV, "version": __version__})

    await connect_to_mongo()
    await init_database()
    await run_seed()
    logger.info("Application startup complete")

    yield

    await close_mongo_connection()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        description=_DESCRIPTION,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True},
    )

    # ---- Rate limiting ----
    app.state.limiter = limiter

    # ---- Middleware (order matters: last added runs first) ----
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time-ms"],
    )

    # ---- Exception handlers ----
    register_exception_handlers(app)

    # ---- Routes ----
    api_router.include_router(elder_care.router, prefix="/elder-care", tags=["elder-care"])
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Health"], summary="Root")
    async def root() -> dict:
        return success_response(
            data={"name": settings.APP_NAME, "version": __version__, "docs": "/docs"},
            message="Home Physio India API is running",
        )

    @app.get("/health", tags=["Health"], summary="Health check")
    async def health(response: __import__('fastapi').Response) -> dict:
        db_ok = await ping()
        
        # Calculate uptime
        uptime_seconds = int(time.time() - START_TIME)
        
        # Check active services based on config
        services = {
            "database": "connected" if db_ok else "disconnected",
            "cloudinary": "configured" if settings.cloudinary_enabled else "missing_config",
            "firebase": "configured" if settings.firebase_enabled else "missing_config",
            "email_resend": "configured" if settings.email_enabled else "missing_config",
        }
        
        status_code = 200 if db_ok else 503
        response.status_code = status_code
        
        return success_response(
            data={
                "status": "ok" if db_ok else "degraded",
                "uptime_seconds": uptime_seconds,
                "environment": settings.APP_ENV,
                "version": __version__,
                "services": services
            },
            message="Health check completed",
        )

    return app


app = create_app()
