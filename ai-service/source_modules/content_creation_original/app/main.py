"""EDUnation Content Creation Module — app factory.

Lifespan: DB init → job workers → provider health snapshot.
Errors: consistent envelope {error: {code, message, request_id}} — never a
stack trace. Versioned under /api/v1."""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .core.config import get_settings
from .core.exceptions import ContentError
from .core.logging import get_logger, request_id_ctx
from .db import get_database

log = get_logger("app")


async def upload_size_guard(request: Request, call_next):
    """Reject oversized upload requests EARLY (before the multipart body is
    parsed), based on Content-Length when the client provides it. Application
    -level bounded reading (read_bounded) remains the authoritative check for
    chunked/lying clients."""
    if request.url.path.startswith("/api/v1/content/documents/upload"):
        length_header = request.headers.get("content-length")
        if length_header:
            try:
                length = int(length_header)
            except ValueError:
                return JSONResponse(status_code=422, content={"error": {
                    "code": "INVALID_REQUEST", "message": "Malformed Content-Length.",
                    "request_id": request_id_ctx.get()}})
            limit = get_settings().max_upload_mb * 1024 * 1024
            # small slack for multipart framing overhead (~64KB)
            if length > limit + 64 * 1024:
                return JSONResponse(status_code=413, content={"error": {
                    "code": "FILE_TOO_LARGE",
                    "message": f"File exceeds the {get_settings().max_upload_mb} MB limit.",
                    "request_id": request_id_ctx.get()}})
    return await call_next(request)


def validate_production_config(settings) -> None:
    """Fail-safe production configuration: authentication must never silently
    become open because CONTENT_API_KEY is missing. Dev/test may run without
    an explicit key (documented open mode for local development only)."""
    if settings.is_prod and not settings.api_key_explicit:
        raise RuntimeError(
            "CONTENT_API_KEY must be set to an explicit random value in "
            "production — refusing to start with open authentication.")
    if settings.is_prod and not settings.signing_secret_explicit:
        raise RuntimeError(
            "ASSET_SIGNING_SECRET must be set to an explicit stable value in "
            "production (signed URLs must verify across instances and "
            "survive restarts) — refusing to start with an ephemeral secret.")
    if settings.is_prod and settings.malware_scanner != "clamav":
        raise RuntimeError(
            "MALWARE_SCANNER must be set to 'clamav' in production "
            "(REQUIRE_MALWARE_SCANNING=true recommended) — refusing to start "
            "with malware scanning disabled. See SECURITY.md.")
    if settings.is_prod and settings.storage_provider == "supabase" and not (
            settings.supabase_url and settings.supabase_service_key):
        raise RuntimeError(
            "STORAGE_PROVIDER=supabase requires SUPABASE_URL and "
            "SUPABASE_SERVICE_KEY in production — refusing to start (no "
            "silent fallback to local storage).")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    validate_production_config(settings)
    database = get_database()
    database.init()
    from .workers.worker import executor, register_handlers
    register_handlers()
    await executor.start()
    health = provider_health()
    log.info("content_module_ready", extra={"ctx": {
        "env": settings.env, "llm": health["llm"], "vector": health["vector"],
        "storage": health["storage"], "tts": health["tts"], "stt": health["stt"],
        "image": health["image"], "video": health["video"],
        "observability": health["observability"]}})
    yield
    await executor.stop()


def provider_health() -> dict:
    """Non-secret readiness snapshot (spec #48)."""
    s = get_settings()
    return {
        "llm": "openrouter" if s.openrouter_api_key else "mock",
        "groq_fallback": bool(s.groq_api_key),
        "openai_fallback": bool(s.openai_api_key),
        "image": "gemini" if s.gemini_api_key else "unconfigured",
        "video": "gemini-veo" if s.gemini_api_key else "unconfigured",
        "tts": "elevenlabs" if s.elevenlabs_api_key else (
            "openai" if s.openai_api_key else "unconfigured"),
        "stt": "deepgram" if s.deepgram_api_key else (
            "openai" if s.openai_api_key else "unconfigured"),
        "vector": "qdrant" if (s.qdrant_url and s.qdrant_api_key) else "memory",
        "storage": s.storage_provider if (
            s.storage_provider != "supabase" or s.supabase_service_key) else "local(fallback)",
        "observability": "langfuse" if (s.langfuse_secret_key and s.langfuse_public_key) else "null",
    }


def create_app() -> FastAPI:
    app = FastAPI(
        title="EDUnation Content Creation Module",
        description="Self-contained generative content engine for the EDUnation "
                    "platform: text, assessments, document-grounded generation, "
                    "diagrams, images, audio and video — behind provider "
                    "abstractions with verification and cost control.",
        version="1.0.0", lifespan=lifespan,
        docs_url="/api/v1/docs", openapi_url="/api/v1/openapi.json")

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        from fastapi.responses import JSONResponse as _JR
        request_id = uuid.uuid4().hex[:12]
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except ContentError as exc:
            response = _JR(status_code=exc.status_code, content=exc.payload(request_id))
        except Exception as exc:  # noqa: BLE001 — controlled envelope, no traceback
            log.error("unhandled", extra={"ctx": {"err": str(exc)[:300],
                                                  "path": request.url.path}})
            response = _JR(status_code=500, content={"error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "request_id": request_id}})
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        log.info("http_request", extra={"ctx": {
            "method": request.method, "path": request.url.path,
            "status": response.status_code,
            "ms": int((time.perf_counter() - started) * 1000)}})
        return response

    app.middleware("http")(upload_size_guard)

    @app.exception_handler(ContentError)
    async def content_error(request: Request, exc: ContentError):
        return JSONResponse(status_code=exc.status_code,
                            content=exc.payload(request_id_ctx.get()))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"error": {
            "code": "INVALID_REQUEST",
            "message": "The request was invalid. Please check your input.",
            "request_id": request_id_ctx.get()}})

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.error("unhandled", extra={"ctx": {"err": str(exc)[:300],
                                              "path": request.url.path}})
        return JSONResponse(status_code=500, content={"error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred.",
            "request_id": request_id_ctx.get()}})

    from .api.routes import assessments, content, documents, jobs
    app.include_router(content.router, prefix="/api/v1/content")
    app.include_router(assessments.router, prefix="/api/v1/content")
    app.include_router(documents.router, prefix="/api/v1/content")
    app.include_router(jobs.router, prefix="/api/v1/content")

    @app.get("/health")
    def health():
        """Public liveness — minimal by design (no infrastructure detail for
        reconnaissance). Same 200-on-healthy semantics used by the Docker
        HEALTHCHECK and load balancers."""
        return {"status": "ok", "module": "content-creation"}

    @app.get("/internal/health")
    async def internal_health(x_api_key: str | None = Header(default=None)):
        """Detailed readiness/provider snapshot — module callers only."""
        from .api.dependencies import require_api_key
        require_api_key(x_api_key)
        s = get_settings()
        return {"status": "ok", "module": "content-creation",
                "llm_mode": s.effective_llm_mode, "providers": provider_health()}

    return app


app = create_app()