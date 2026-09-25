"""Error hierarchy — consistent client envelope, no stack traces leaked."""
from __future__ import annotations

from typing import Optional


class ContentError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    message = "An unexpected error occurred."

    def __init__(self, message: Optional[str] = None, *, detail_log: Optional[str] = None) -> None:
        self.message = message or self.message
        self.detail_log = detail_log or self.message
        super().__init__(self.detail_log)

    def payload(self, request_id: str = "-") -> dict:
        return {"error": {"code": self.code, "message": self.message, "request_id": request_id}}


class UnauthorizedError(ContentError):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "A valid X-API-Key header is required."


class ForbiddenError(ContentError):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have access to this resource."


class NotFoundError(ContentError):
    status_code = 404
    code = "NOT_FOUND"
    message = "The requested resource was not found."


class ValidationError(ContentError):
    status_code = 422
    code = "INVALID_REQUEST"
    message = "The request was invalid."


class RateLimitedError(ContentError):
    status_code = 429
    code = "RATE_LIMITED"
    message = "Too many requests. Please slow down."


class QuotaExceededError(ContentError):
    status_code = 402
    code = "QUOTA_EXCEEDED"
    message = "Generation quota exceeded for this student."


class UnsupportedFileError(ContentError):
    status_code = 422
    code = "UNSUPPORTED_FILE_TYPE"
    message = "This file type is not supported."


class FileTooLargeError(ContentError):
    status_code = 413
    code = "FILE_TOO_LARGE"
    message = "The uploaded file exceeds the size limit."


class GenerationError(ContentError):
    status_code = 502
    code = "CONTENT_GENERATION_FAILED"
    message = "Unable to generate the requested content."


class SchemaValidationError(ContentError):
    status_code = 502
    code = "SCHEMA_VALIDATION_FAILED"
    message = "Generated content failed structural validation."


class ProviderUnavailableError(ContentError):
    status_code = 503
    code = "PROVIDER_UNAVAILABLE"
    message = "The required generation provider is not configured."

    def __init__(self, message: Optional[str] = None, *, code: Optional[str] = None) -> None:
        super().__init__(message)
        if code:
            self.code = code  # e.g. IMAGE_PROVIDER_UNAVAILABLE


class InsufficientSourceError(ContentError):
    status_code = 422
    code = "INSUFFICIENT_SOURCE"
    message = "Insufficient information in the provided material."


class JobFailedError(ContentError):
    status_code = 500
    code = "JOB_FAILED"
    message = "The generation job failed."