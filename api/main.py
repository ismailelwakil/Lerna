"""
Academic OS - Thin Backend & Integration API Facade
Production-ready for Railway (PORT, CORS_ORIGINS, proxy headers).
"""
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
AI_SERVICE_DIR = ROOT_DIR / "ai-service"

if AI_SERVICE_DIR.exists() and str(AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(AI_SERVICE_DIR / ".env")
except ImportError:
    pass

from api.routes import (
    health_router,
    profile_router,
    tutor_router,
    materials_router,
    study_tools_router,
    assessments_router,
    spaced_repetition_router,
    artifacts_router,
)

app = FastAPI(
    title="Academic OS Integration API",
    description=(
        "Thin API Integration Facade connecting the React Frontend to the "
        "Academic OS Python Learning Intelligence Subsystem."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


_origins = _cors_origins()
# Starlette forbids credentials=True with allow_origins=["*"]
_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true" and _origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(health_router)
app.include_router(profile_router)
app.include_router(tutor_router)
app.include_router(materials_router)
app.include_router(study_tools_router)
app.include_router(assessments_router)
app.include_router(spaced_repetition_router)
app.include_router(artifacts_router)


@app.get("/", tags=["System"])
def root():
    """Lightweight liveness probe — does not initialize the AI engine (Railway healthcheck)."""
    return {
        "name": "Academic OS Integration API",
        "version": "1.0.0",
        "status": "online",
        "documentation": "/docs",
        "openapi_schema": "/openapi.json",
        "health": "/health",
        "capabilities": "/capabilities",
    }


@app.get("/livez", tags=["System"])
def livez():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)
