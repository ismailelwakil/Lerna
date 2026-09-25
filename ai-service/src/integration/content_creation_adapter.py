from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class ContentLearnerContext(BaseModel):
    level: str = 'beginner'
    major: str | None = None
    course: str | None = None
    learning_goal: str | None = None
    concept_mastery: dict[str, float] = Field(default_factory=dict)
    knowledge_gaps: list[str] = Field(default_factory=list)
    unknown_concepts: list[str] = Field(default_factory=list)
    prerequisite_gaps: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    strong_areas: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    learning_preferences: list[str] = Field(default_factory=list)
    previous_content_performance: dict[str, Any] = Field(default_factory=dict)

def _level(profile):
    vals = list(getattr(profile, "concept_mastery", {}).values())
    avg = sum(vals) / len(vals) if vals else 0.0
    return 'advanced' if avg >= 0.8 else ('intermediate' if avg >= 0.55 else 'beginner')

def build_content_creation_context(profile) -> ContentLearnerContext:
    recent = getattr(profile, "assessment_history", [])[-5:]
    avg = sum(float(x.get('score', 0)) for x in recent) / len(recent) if recent else 0.0
    student = getattr(profile, "student", None)
    course = getattr(student, "course", None) if student else getattr(profile, "course", None)
    preference = getattr(student, "learning_preference", "step-by-step") if student else "step-by-step"
    unknown = list(getattr(profile, "unknown_concepts", []) or [])
    weak = list(getattr(profile, "weak_concepts", []) or [])
    strengths = list(getattr(profile, "strengths", []) or [])
    misconceptions = list(getattr(profile, "misconceptions", []) or [])
    prereqs = list(getattr(profile, "prerequisite_gaps", []) or [])
    mastery = dict(getattr(profile, "concept_mastery", {}) or {})
    
    gaps = unknown if unknown else weak

    return ContentLearnerContext(
        level=_level(profile),
        course=course,
        learning_goal=getattr(profile, "learning_goal", None),
        concept_mastery=mastery,
        knowledge_gaps=gaps,
        unknown_concepts=unknown,
        prerequisite_gaps=prereqs,
        misconceptions=misconceptions,
        strong_areas=strengths,
        weak_areas=weak,
        learning_preferences=[preference],
        previous_content_performance={'assessment_avg': round(avg, 3)},
    )
