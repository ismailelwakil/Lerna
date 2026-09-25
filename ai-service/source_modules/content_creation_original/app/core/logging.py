"""Structured JSON logging with request correlation and secret redaction."""
from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

REDACT = {"api_key", "authorization", "key", "token", "secret", "password"}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        extra = getattr(record, "ctx", None)
        if isinstance(extra, dict):
            entry.update({k: ("***" if k.lower() in REDACT else v) for k, v in extra.items()})
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)[-1500:]
        return json.dumps(entry, default=str)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"content.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_event(name: str, **ctx) -> None:
    get_logger(name).info(ctx.pop("event", name), extra={"ctx": ctx})