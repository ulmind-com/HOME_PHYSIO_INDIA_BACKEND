"""Centralised application settings loaded from environment variables.

Uses ``pydantic-settings`` (Pydantic v2) so every value is typed, validated
and available through a single cached ``Settings`` instance.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    All values are read from the process environment (or a local ``.env``
    file in development). Anything sensitive must be supplied via environment
    variables in production (Render dashboard, Docker secrets, etc.).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- Application ----
    APP_NAME: str = "Home Physio India"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ---- Security / JWT ----
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # ---- Database ----
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "home_physio_india"

    # ---- Cloudinary ----
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    CLOUDINARY_URL: str = ""

    # ---- Email (SMTP) ----
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Home Physio India"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    ADMIN_NOTIFICATION_EMAIL: str = ""

    # ---- CORS ----
    # Comma-separated string in the environment; use ``cors_origins`` for the
    # parsed list (avoids pydantic-settings JSON-decoding complex env values).
    CORS_ORIGINS: str = "*"

    # ---- Rate limiting ----
    RATE_LIMIT_DEFAULT: str = "200/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    # ---- Frontend ----
    FRONTEND_URL: str = "http://localhost:3000"

    # ---- Bootstrap admin ----
    FIRST_ADMIN_NAME: str = "Super Admin"
    FIRST_ADMIN_EMAIL: str = "admin@homephysioindia.com"
    FIRST_ADMIN_PASSWORD: str = "Admin@1234Secure!"

    @property
    def cors_origins(self) -> List[str]:
        """Return CORS origins parsed from the comma-separated string."""
        raw = self.CORS_ORIGINS.strip()
        if not raw:
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Return ``True`` when running in a production-like environment."""
        return self.APP_ENV.lower() in {"production", "prod"}

    @property
    def email_enabled(self) -> bool:
        """Return ``True`` only when SMTP is fully configured."""
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD)

    @property
    def cloudinary_enabled(self) -> bool:
        """Return ``True`` only when Cloudinary credentials are present."""
        return bool(
            self.CLOUDINARY_CLOUD_NAME
            and self.CLOUDINARY_API_KEY
            and self.CLOUDINARY_API_SECRET
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance (dependency-injectable)."""
    return Settings()  # type: ignore[call-arg]


# Module-level singleton for convenient imports.
settings: Settings = get_settings()
