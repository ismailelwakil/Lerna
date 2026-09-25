"""Assessment request/response schemas."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .common import BaseContentRequest, Difficulty


class AssessmentRequest(BaseContentRequest):
    num_questions: int = Field(default=10, ge=1, le=50)
    difficulty: Difficulty = Difficulty.MEDIUM
    mix_difficulty: bool = True
    question_types: list[Literal["MCQ", "TRUE_FALSE", "SHORT_ANSWER", "LONG_ANSWER",
                                 "CODING", "PRACTICAL", "SCENARIO"]] = Field(
        default_factory=lambda: ["MCQ", "TRUE_FALSE", "SHORT_ANSWER"])
    learning_objectives: list[str] = Field(default_factory=list, max_length=15)
    include_answers: bool = True   # only trusted callers (tutor backend) keep keys
    instructions: Optional[str] = Field(default=None, max_length=1000)


class QuestionOut(BaseModel):
    question_id: str
    index: int
    type: str
    question: str
    options: list[str] = Field(default_factory=list)
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: str = "medium"
    blooms: str = "UNDERSTAND"
    learning_objective: str = ""
    source_reference: Optional[dict] = None


class QuestionSetOut(BaseModel):
    set_id: str
    kind: str
    topic: str
    difficulty: str
    student_level: str
    document_id: Optional[str] = None
    total: int
    questions: list[QuestionOut]
    meta: dict = {}


class BankFilter(BaseModel):
    student_id: str = Field(min_length=1, max_length=64,
                            pattern=r"^[A-Za-z0-9_-]+$")
    topic: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    question_type: Optional[str] = None
    learning_objective: Optional[str] = None
    document_id: Optional[str] = None
    limit: int = Field(default=25, ge=1, le=100)
    randomize: bool = True
    include_answers: bool = True