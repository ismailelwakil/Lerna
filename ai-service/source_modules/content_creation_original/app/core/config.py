"""Configuration — fully environment driven (.env supported)."""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


def _load_dotenv() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def _s(name: str, default: str = "") -> str:
    v = os.environ.get(name)
    return default if v is None or v == "" else v


def _opt(name: str) -> Optional[str]:
    v = os.environ.get(name)
    return v if v else None


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _i(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _json(name: str, default):
    try:
        return json.loads(os.environ.get(name) or json.dumps(default))
    except ValueError:
        return default


class Settings:
    def __init__(self) -> None:
        self.env: str = _s("CONTENT_ENV", "dev")
        self.is_prod: bool = self.env.lower() in {"prod", "production"}

        # module access (integration with the EDUnation core backend).
        # The key is only "set" when explicitly configured — production
        # startup refuses to run without it (fail-safe, see app/main.py).
        self.api_key_explicit: bool = bool(_s("CONTENT_API_KEY", ""))
        self.api_key: str = _s("CONTENT_API_KEY", "")

        # LLM (OpenRouter primary)
        self.openrouter_api_key: str = _s("OPENROUTER_API_KEY", "")
        self.openrouter_base: str = _s("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.models: dict[str, str] = {
            "fast": _s("OPENROUTER_FAST_MODEL", "google/gemini-3.8-flash"),
            "reasoning": _s("OPENROUTER_REASONING_MODEL", "openai/gpt-5.6-sol"),
            "content": _s("OPENROUTER_CONTENT_MODEL", "anthropic/claude-fable-5.1"),
            "structured": _s("OPENROUTER_STRUCTURED_MODEL", "google/gemini-3.8-flash"),
        }
        self.llm_mode: str = _s("CONTENT_LLM_MODE", "auto")  # auto | mock
        self.llm_timeout: float = float(_s("LLM_TIMEOUT", "90"))

        # fallback LLMs
        self.groq_api_key: str = _s("GROQ_API_KEY", "")
        self.groq_model: str = _s("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.openai_api_key: str = _s("OPENAI_API_KEY", "")

        # Gemini multimodal
        self.gemini_api_key: str = _s("GEMINI_API_KEY", "")
        self.gemini_base: str = _s("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
        self.gemini_image_model: str = _s("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
        self.gemini_video_model: str = _s("GEMINI_VIDEO_MODEL", "veo-3.0-generate-preview")
        self.gemini_embedding_model: str = _s("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
        self.gemini_embedding_dim: int = _i("GEMINI_EMBEDDING_DIM", 768)

        # voice
        self.elevenlabs_api_key: str = _s("ELEVENLABS_API_KEY", "")
        self.elevenlabs_voice_id: str = _s("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        self.deepgram_api_key: str = _s("DEEPGRAM_API_KEY", "")

        # vector store
        self.qdrant_url: str = _s("QDRANT_URL", "").rstrip("/")
        self.qdrant_api_key: str = _s("QDRANT_API_KEY", "")

        # storage
        self.storage_provider: str = _s("STORAGE_PROVIDER", "local").lower()
        self.storage_bucket: str = _s("STORAGE_BUCKET", "edunation-content")
        self.supabase_url: str = _s("SUPABASE_URL", "").rstrip("/")
        self.supabase_service_key: str = _s("SUPABASE_SERVICE_KEY", "")
        # ephemeral random ONLY for dev/test; production requires an explicit
        # stable secret (validate_production_config fails closed otherwise).
        self.signing_secret_explicit: bool = bool(_s("ASSET_SIGNING_SECRET", ""))
        self.signing_secret: str = _s("ASSET_SIGNING_SECRET", "") or secrets.token_urlsafe(32)
        self.signed_url_ttl: int = _i("SIGNED_URL_TTL_MINUTES", 30)

        # infra
        self.database_url: str = _s("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'content.db').as_posix()}")
        self.redis_url: str = _s("REDIS_URL", "")

        # observability
        self.langfuse_public_key: str = _s("LANGFUSE_PUBLIC_KEY", "")
        self.langfuse_secret_key: str = _s("LANGFUSE_SECRET_KEY", "")
        self.langfuse_base_url: str = _s("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").rstrip("/")

        # limits / cost control
        self.max_upload_mb: int = _i("MAX_UPLOAD_MB", 25)
        self.max_questions: int = _i("MAX_QUESTIONS", 50)
        self.max_audio_chars: int = _i("MAX_AUDIO_CHARS", 20000)
        self.max_video_jobs_per_day: int = _i("MAX_VIDEO_JOBS_PER_DAY", 5)
        self.max_content_chars: int = _i("MAX_CONTENT_CHARS", 12000)
        self.rate_limits: dict = _json("RATE_LIMITS", {
            "default": "60/60", "generate": "20/60", "upload": "12/60",
            "jobs": "10/60", "expensive": "4/3600",
        })

        # malware scanning: none | clamav  (see services/documents/processor.py)
        self.malware_scanner: str = _s("MALWARE_SCANNER", "none").lower()
        # when true, uploads are REJECTED (job fails safely) if the scanner is
        # configured but unavailable — never silently accepted as "clean".
        self.require_malware_scanning: bool = _bool("REQUIRE_MALWARE_SCANNING", False)
        self.clamav_host: str = _s("CLAMAV_HOST", "127.0.0.1")
        self.clamav_port: int = _i("CLAMAV_PORT", 3310)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def effective_llm_mode(self) -> str:
        if self.llm_mode == "mock":
            return "mock"
        return "openrouter" if self.openrouter_api_key else "mock"

    def rate_limit(self, kind: str) -> tuple[int, int]:
        raw = self.rate_limits.get(kind) or self.rate_limits["default"]
        try:
            count, _, seconds = raw.partition("/")
            return int(count), int(seconds)
        except ValueError:
            return 30, 60


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> Settings:
    global _settings
    _settings = Settings()
    return _settings