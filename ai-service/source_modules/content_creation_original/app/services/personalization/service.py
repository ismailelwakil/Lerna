"""Personalization (spec #6, #9, #22) — learner context (owned by the main
platform) shapes every prompt: level directives, gaps, misconceptions, language,
adaptive re-explanation strategies."""
from __future__ import annotations

from ...schemas.common import LearnerContext, StudentLevel

# Adaptive explanation ladder (spec #9): never repeat the same strategy twice.
RE_EXPLAIN_LADDER = ["simple", "analogy", "real_world", "visual",
                     "step_by_step", "practice", "prerequisite"]


def learner_dict(learner: LearnerContext | None, level: StudentLevel | str) -> dict:
    data = learner.model_dump() if learner else {}
    data["level"] = str(level)
    return data


def next_strategy(previous: str | None, requested: str | None) -> str:
    """Pick a DIFFERENT teaching strategy when the learner asks again."""
    if requested:
        return requested
    if not previous:
        return "simple"
    try:
        index = RE_EXPLAIN_LADDER.index(previous)
    except ValueError:
        return "analogy"
    return RE_EXPLAIN_LADDER[(index + 1) % len(RE_EXPLAIN_LADDER)]


def scene_count_for_level(level: str, duration_seconds: int) -> int:
    """Video personalization (spec #22): beginners get fewer, slower scenes."""
    base = duration_seconds // 30
    factor = {"beginner": 0.7, "intermediate": 1.0, "advanced": 1.2, "expert": 1.3}
    return max(3, min(8, int(base * factor.get(level, 1.0))))


def narration_style_note(level: str) -> str:
    return {
        "beginner": "Slow pace, short sentences, define every term.",
        "intermediate": "Moderate pace, practical vocabulary.",
        "advanced": "Brisk pace, technical vocabulary, nuance.",
        "expert": "Dense expert narration, trade-offs and edge cases.",
    }.get(level, "")