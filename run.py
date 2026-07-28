"""Local development entrypoint.

Usage::

    python run.py

Runs the API with hot-reload using the host/port from settings.
For production use gunicorn (see the Dockerfile / render.yaml).
"""

import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
