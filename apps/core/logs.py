"""Structured logging: one JSON object per line in production, readable text in development.

Every log line made while handling a web request carries that request's id, so a single request can
be followed through the logs. The same id is sent back in the ``X-Request-ID`` response header.
Standard library only, so there is nothing extra to install or keep up to date.
"""

from __future__ import annotations

import contextvars
import json
import logging
from datetime import UTC, datetime

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

# Attributes every LogRecord has. Anything else was passed with ``extra=`` and is worth keeping.
_STANDARD = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class RequestIdFilter(logging.Filter):
    """Copies the current request id onto every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Formats a record as a single line of JSON, including any ``extra=`` fields."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if getattr(record, "request_id", ""):
            entry["request_id"] = record.request_id
        for key, value in record.__dict__.items():
            if key not in _STANDARD and key != "request_id" and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str, ensure_ascii=False)


def build_logging(fmt: str = "text", level: str = "INFO") -> dict:
    """A ``LOGGING`` setting that sends everything to standard output, where Docker collects it."""
    formatter = (
        {"()": "apps.core.logs.JsonFormatter"}
        if fmt == "json"
        else {"format": "%(asctime)s %(levelname)-7s %(name)s %(request_id)s %(message)s"}
    )
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"request_id": {"()": "apps.core.logs.RequestIdFilter"}},
        "formatters": {"main": formatter},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "main",
                "filters": ["request_id"],
            }
        },
        "root": {"handlers": ["console"], "level": level},
        # Django attaches its own handlers to these; clear them so each line is written once.
        "loggers": {
            "django": {"handlers": [], "propagate": True},
            "django.server": {"handlers": [], "propagate": True},
        },
    }
