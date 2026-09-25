from __future__ import annotations
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore', case_sensitive=False)

    data_dir: str = 'data'
    ai_provider: str = 'auto'
    ai_model: str = ''
    ai_fallback_providers: str = 'gemini,openai,anthropic,groq'
    gemini_api_key: str | None = Field(default=None, repr=False)
    openai_api_key: str | None = Field(default=None, repr=False)
    anthropic_api_key: str | None = Field(default=None, repr=False)
    groq_api_key: str | None = Field(default=None, repr=False)
    embedding_backend: str = 'auto'
    embedding_model: str = 'intfloat/multilingual-e5-small'
    vector_backend: str = 'auto'
    chroma_path: str = 'data/chroma'
    allow_mock_fallback: bool = False
    enable_web_search: bool = False
    tavily_api_key: str | None = Field(default=None, repr=False)
    max_upload_mb: int = 25
    retrieval_top_k: int = 6
    retrieval_candidate_k: int = 18
    evidence_min_confidence: float = 0.30
    trust_threshold: float = 0.80
    artifacts_dir: str = 'data/artifacts'

    # Demo-only authenticated learner context for the standalone Streamlit UI.
    # In the full Academic OS these values are supplied by the host session.
    demo_student_id: str = 'student-001'
    demo_student_name: str = 'Demo Student'
    demo_course: str = 'Artificial Intelligence'
    demo_language: str = 'en'
    demo_learning_preference: str = 'step-by-step'

    @property
    def fallback_providers(self) -> tuple[str, ...]:
        return tuple(x.strip().lower() for x in self.ai_fallback_providers.split(',') if x.strip())

    @property
    def provider_keys(self) -> dict[str, str]:
        pairs={'gemini':self.gemini_api_key,'openai':self.openai_api_key,'anthropic':self.anthropic_api_key,'groq':self.groq_api_key}
        return {k:v for k,v in pairs.items() if v}

    def ensure_directories(self) -> None:
        for p in (self.data_dir, self.chroma_path, self.artifacts_dir):
            Path(p).mkdir(parents=True, exist_ok=True)