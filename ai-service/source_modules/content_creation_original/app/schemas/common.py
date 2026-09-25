"""Pydantic contracts — every endpoint has typed request/response schemas."""
from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ContentType(str, Enum):
    EXPLANATION = "explanation"
    SUMMARY = "summary"
    NOTES = "notes"
    STUDY_GUIDE = "study_guide"
    EXAMPLE = "example"
    ANALOGY = "analogy"
    COMPARISON = "comparison"
    FLASHCARDS = "flashcards"
    QUIZ = "quiz"
    EXAM = "exam"
    QUESTION_BANK = "question_bank"
    PRACTICE = "practice"
    CODING_EXERCISE = "coding_exercise"
    DIAGRAM = "diagram"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    INTERACTIVE_LESSON = "interactive_lesson"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class StudentLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class Blooms(str, Enum):
    REMEMBER = "REMEMBER"
    UNDERSTAND = "UNDERSTAND"
    APPLY = "APPLY"
    ANALYZE = "ANALYZE"
    EVALUATE = "EVALUATE"
    CREATE = "CREATE"


class ExplanationStrategy(str, Enum):
    SIMPLE = "simple"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    STEP_BY_STEP = "step_by_step"
    REAL_WORLD = "real_world"
    ANALOGY = "analogy"
    VISUAL = "visual"
    PRACTICE = "practice"
    PREREQUISITE = "prerequisite"


class LearnerContext(BaseModel):
    """Provided BY the main EDUnation platform — this module never owns it."""
    level: StudentLevel = StudentLevel.BEGINNER
    major: Optional[str] = None
    course: Optional[str] = None
    learning_goal: Optional[str] = None
    knowledge_gaps: list[str] = Field(default_factory=list, max_length=20)
    misconceptions: list[str] = Field(default_factory=list, max_length=20)
    strong_areas: list[str] = Field(default_factory=list, max_length=20)
    weak_areas: list[str] = Field(default_factory=list, max_length=20)
    learning_preferences: list[str] = Field(default_factory=list, max_length=10)
    previous_content_performance: Optional[dict] = None


class BaseContentRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=64,
                            pattern=r"^[A-Za-z0-9_-]+$")
    course_id: Optional[str] = Field(default=None, max_length=64)
    topic: str = Field(min_length=1, max_length=300)
    inline_material: Optional[str] = Field(default=None, max_length=50000)
    document_ids: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("document_ids")
    @classmethod
    def _ids_ok(cls, values: list[str]) -> list[str]:
        for value in values:
            if not value or len(value) > 64 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
                raise ValueError("document_ids must be 1-64 chars [A-Za-z0-9_-]")
        return values
    level: StudentLevel = StudentLevel.BEGINNER
    language: str = Field(default="en", pattern="^(en|ar)$")
    length: str = Field(default="medium", pattern="^(short|medium|long)$")
    allow_external_knowledge: bool = False
    learner: LearnerContext = Field(default_factory=LearnerContext)


class ContentMetaOut(BaseModel):
    content_id: str
    type: str
    topic: str
    difficulty: str
    student_level: str
    source_ids: list[str] = Field(default_factory=list)
    source_refs: list = Field(default_factory=list
    )
    created_at: str
    version: int = 1
    verified: bool = False
    verification: dict = Field(default_factory=dict)
    grounded: bool = True
    provider: Optional[str] = None
    model: Optional[str] = None
    usage: dict = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0


class Envelope(BaseModel):
    meta: ContentMetaOut
    content: dict