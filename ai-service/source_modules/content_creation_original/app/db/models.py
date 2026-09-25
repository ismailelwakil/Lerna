"""SQLAlchemy models — only entities owned by the Content Creation module.

Learner/course identities are integration references (student_id/course_id
strings owned by the main EDUnation platform)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text)
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sid() -> str:
    import uuid
    return uuid.uuid4().hex


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"
    __table_args__ = (Index("ix_docs_student", "student_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=sid)
    student_id: Mapped[str] = mapped_column(String(64))
    course_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    ext: Mapped[str] = mapped_column(String(16))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_key: Mapped[str] = mapped_column(String(400))
    status: Mapped[str] = mapped_column(String(24), default="uploaded")
    # uploaded | processing | processed | failed
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    doc_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (Index("ix_chunks_doc", "document_id", "chunk_index"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=sid)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("uploaded_documents.id", ondelete="CASCADE"))
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, default="")
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slide: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(300), nullable=True)
    indexed: Mapped[bool] = mapped_column(Boolean, default=False)  # vector-stored
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentItem(Base):
    __tablename__ = "content_items"
    __table_args__ = (Index("ix_content_student_type", "student_id", "type"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=sid)
    student_id: Mapped[str] = mapped_column(String(64))
    course_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    type: Mapped[str] = mapped_column(String(32))          # explanation|quiz|...
    topic: Mapped[str] = mapped_column(String(300), default="")
    title: Mapped[str] = mapped_column(String(300), default="")
    difficulty: Mapped[str] = mapped_column(String(16), default="medium")
    student_level: Mapped[str] = mapped_column(String(16), default="beginner")
    body: Mapped[dict] = mapped_column(JSON, default=dict)
    source_ids: Mapped[list] = mapped_column(JSON, default=list)
    source_refs: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class QuestionSet(Base):
    __tablename__ = "question_sets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=sid)
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    course_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(24))   # quiz|exam|question_bank|practice
    topic: Mapped[str] = mapped_column(String(300), default="")
    difficulty: Mapped[str] = mapped_column(String(16), default="medium")
    student_level: Mapped[str] = mapped_column(String(16), default="beginner")
    document_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content_item_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (Index("ix_questions_set", "set_id", "index"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=sid)
    set_id: Mapped[str] = mapped_column(ForeignKey("question_sets.id", ondelete="CASCADE"))
    index: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(24))           # MCQ|TRUE_FALSE|SHORT|...
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON, default=list)
    correct_answer: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(16), default="medium")
    blooms: Mapped[str] = mapped_column(String(16), default="UNDERSTAND")
    objective: Mapped[str] = mapped_column(String(300), default="")
    source_ref: Mapped[dict] = mapped_column(JSON, default=dict)
    valid: Mapped[bool] = mapped_column(Boolean, default=True)


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (Index("ix_jobs_student", "student_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=sid)
    student_id: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(32))          # document_process|audio|video|exam
    status: Mapped[str] = mapped_column(String(32), default="QUEUED")
    # QUEUED|PLANNING|SCRIPTING|VERIFYING|SCENE_GENERATION|VIDEO_GENERATION|
    # ASSEMBLING|QUALITY_CHECK|PROCESSING|COMPLETED|FAILED|CANCELLED
    progress: Mapped[int] = mapped_column(Integer, default=0)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class GeneratedAsset(Base):
    __tablename__ = "generated_assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=sid)
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(16))          # image|audio|video|subtitle
    storage_key: Mapped[str] = mapped_column(String(400))
    mime: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    job_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content_item_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    asset_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ProviderRequest(Base):
    """Cost/usage telemetry per external call (spec #35)."""
    __tablename__ = "provider_requests"
    __table_args__ = (Index("ix_provider_student_time", "student_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=sid)
    student_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120), default="")
    request_type: Mapped[str] = mapped_column(String(60), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    est_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="ok")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentVerification(Base):
    __tablename__ = "content_verifications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=sid)
    content_item_id: Mapped[str] = mapped_column(String(32), index=True)
    checker: Mapped[str] = mapped_column(String(40), default="rules")
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)