"""API dependencies — integration auth (X-API-Key), authoritative student
identity, rate limiting, quotas.

SECURITY MODEL (authoritative identity):
- The caller authenticates the module with X-API-Key (server-to-server).
- The end-user identity is the X-Student-Id header, forwarded by the trusted
  main platform. A student_id inside a request body is *advisory only*: it
  must match the authenticated header identity or the request is rejected
  (403). All ownership operations use the authenticated identity — never a
  client-supplied body value.
"""
from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Header, Request

from ..core.config import get_settings
from ..core.exceptions import ForbiddenError, UnauthorizedError, ValidationError
from ..core.logging import log_event
from ..core.security import enforce_rate
from ..services.telemetry import telemetry

import re as _re
_STUDENT_RX = _re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_STUDENT_PATTERN_OK = lambda value: bool(value) and _STUDENT_RX.fullmatch(value)


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.api_key_explicit:
        return  # dev/test without CONTENT_API_KEY → open (production startup
                # refuses to run without an explicit key; see app/main.py)
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise UnauthorizedError()


def student_identity(
    x_api_key: Optional[str] = Header(default=None),
    x_student_id: Optional[str] = Header(default=None),
) -> str:
    """Authenticate the module call and return the AUTHORITATIVE student id."""
    require_api_key(x_api_key)
    if not _STUDENT_PATTERN_OK(x_student_id):
        raise ValidationError("X-Student-Id header is required (1-64 chars).")
    return x_student_id  # type: ignore[return-value]


def authorize_student(authenticated: str, body_student_id: Optional[str]) -> str:
    """Body student_id may not override the authenticated identity.

    Returns the authenticated identity for all ownership operations.
    Raises 403 on conflict (spoofing attempt)."""
    if body_student_id is not None and body_student_id != authenticated:
        raise ForbiddenError(
            "Authenticated identity does not match the request body.")
    return authenticated


def student_context(
    x_api_key: Optional[str] = Header(default=None),
    x_student_id: Optional[str] = Header(default=None),
) -> str:
    """Legacy alias kept for backward compatibility with internal callers."""
    return student_identity(x_api_key, x_student_id)


def rate(kind: str):
    def _dependency(request: Request, x_api_key: Optional[str] = Header(default=None)) -> None:
        require_api_key(x_api_key)
        student = request.headers.get("x-student-id", "anon")
        enforce_rate(kind, f"{student[:64]}")
    return _dependency


def quota_guard(student_id: str) -> None:
    """Per-student cost/quota abuse prevention (spec #35)."""
    telemetry.check_student_quota(student_id)


def audit(event: str, *, student_id: str = "", **ctx) -> None:
    log_event(event, student_id=student_id[:16], **ctx)