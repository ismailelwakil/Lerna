"""Document + media + jobs schemas."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .common import BaseContentRequest, ExplanationStrategy


class DocumentOut(BaseModel):
    document_id: str
    filename: str
    ext: str
    size_bytes: int
    status: str
    page_count: int
    chunks: int = 0
    created_at: str
    meta: dict = {}


class ProcessRequest(BaseModel):
    """Trigger extraction + chunking + embedding + vector indexing (async job)."""
    chunk_chars: int = Field(default=1200, ge=300, le=4000)
    overlap: int = Field(default=150, ge=0, le=500)


class FromDocumentRequest(BaseModel):
    """Generic 'do X with my material' request.

    instruction examples: "Summarize this." | "Create 20 MCQs." |
    "Teach me this material." | "Find the difficult concepts."
    """
    student_id: str = Field(min_length=1, max_length=64,
                            pattern=r"^[A-Za-z0-9_-]+$")
    document_ids: list[str] = Field(min_length=1, max_length=10)
    instruction: str = Field(min_length=3, max_length=2000)
    level: str = "beginner"
    language: str = Field(default="en", pattern="^(en|ar)$")
    allow_external_knowledge: bool = False


class ExplainRequest(BaseContentRequest):
    strategy: ExplanationStrategy = ExplanationStrategy.SIMPLE
    focus: Optional[str] = Field(default=None, max_length=500)
    re_explain_of: Optional[str] = Field(default=None, max_length=32,
                                         description="content_id being re-explained")


class TextRequest(BaseContentRequest):
    """summarize / examples / notes / study-guide"""
    max_items: int = Field(default=10, ge=1, le=30)
    focus: Optional[str] = Field(default=None, max_length=500)


class FlashcardsRequest(BaseContentRequest):
    count: int = Field(default=12, ge=1, le=40)


class DiagramRequest(BaseContentRequest):
    diagram_kind: Literal["flow", "sequence", "auto"] = "auto"
    style_hint: Optional[str] = Field(default=None, max_length=300)


class ImageRequest(BaseContentRequest):
    visual_kind: Literal["illustration", "infographic", "thumbnail"] = "illustration"
    aspect: Literal["1:1", "16:9", "9:16"] = "16:9"


class AudioRequest(BaseContentRequest):
    voice: Optional[str] = Field(default=None, max_length=60)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    text_override: Optional[str] = Field(default=None, max_length=20000)
    async_mode: bool = Field(default=False,
                             description="large content → job with status polling")


class VideoRequest(BaseContentRequest):
    duration_seconds: int = Field(default=180, ge=30, le=600)
    voice: Optional[str] = None
    style: Literal["narrated-slides", "animated-diagram"] = "narrated-slides"


class VerifyRequest(BaseModel):
    content_id: str = Field(min_length=1, max_length=64,
                            pattern=r"^[A-Za-z0-9_-]+$")
    strict: bool = True


class JobCreateRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=64,
                            pattern=r"^[A-Za-z0-9_-]+$")
    kind: Literal["document_process", "audio", "video", "exam", "embeddings"]
    params: dict = Field(default_factory=dict)


class JobOut(BaseModel):
    job_id: str
    kind: str
    status: str
    progress: int = 0
    result: dict = Field(default_factory=dict)
    error: str = ""
    created_at: str
    updated_at: str


class AssetOut(BaseModel):
    asset_id: str
    kind: str
    mime: str
    size_bytes: int
    url: str
    expires_at: Optional[str] = None
    meta: dict = {}