"""Structured JSON logging configuration.

Emits one JSON object per log line so logs are machine-parseable by
aggregators (Render, Datadog, ELK, ...). A request-id context var makes it
possible to correlate all log lines belonging to a single HTTP request.
"""

from __future__ import annotations

import contextvars
import datetime as dt
import json
import logging
import sys
from typing import Any, Dict

# Correlation id for the current request (set by middleware).
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON documents."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Merge any structured "extra" fields passed by callers.
        reserved = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)
        reserved.update({"message", "asctime"})
        for key, value in record.__dict__.items():
            if key not in reserved and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(debug: bool = False) -> None:
    """Configure root logging with the JSON formatter.

    Args:
        debug: When ``True`` the log level is ``DEBUG`` otherwise ``INFO``.
    """
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Tame noisy third-party loggers.
    for noisy in ("uvicorn.access", "uvicorn.error", "pymongo", "motor"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
