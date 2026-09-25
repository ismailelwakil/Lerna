"""Question Quality Control (spec #14) — rule-based validation of every
generated question; the exam generator regenerates ONLY failed questions."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from ...schemas.assessment import QuestionOut

_WORDS = re.compile(r"[a-z\u0600-\u06FF0-9]+")


def _normalize(text: str) -> str:
    return " ".join(_WORDS.findall((text or "").lower()))


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a[:400], b[:400]).ratio()


@dataclass
class ValidationReport:
    valid: bool
    issues: list[str] = field(default_factory=list)


def validate_question(q: QuestionOut, source_texts: list[str],
                      existing_prompts: list[str]) -> ValidationReport:
    issues: list[str] = []
    prompt_norm = _normalize(q.question)

    if len(q.question.strip()) < 12:
        issues.append("prompt_too_short")
    if q.type == "MCQ":
        if len(q.options) < 3:
            issues.append("too_few_options")
        if len(set(o.strip().lower() for o in q.options)) != len(q.options):
            issues.append("duplicate_options")
        try:
            answer = q.options[int(q.correct_answer)] if q.correct_answer and \
                str(q.correct_answer).isdigit() else None
        except (ValueError, IndexError):
            answer = None
        if answer is None:
            issues.append("mcq_answer_invalid")
        elif str(q.correct_answer).isdigit() and \
                sum(1 for o in q.options if o.strip().lower() == answer.strip().lower()) > 1:
            issues.append("multiple_correct_options")
    elif q.type == "TRUE_FALSE":
        if str(q.correct_answer).lower() not in {"true", "false"}:
            issues.append("true_false_answer_invalid")
    if not (q.explanation or "").strip():
        issues.append("missing_explanation")
    if q.difficulty not in {"easy", "medium", "hard", "expert"}:
        issues.append("bad_difficulty")

    # duplicate detection inside the set
    for other in existing_prompts:
        if _similarity(prompt_norm, _normalize(other)) > 0.82:
            issues.append("duplicate_prompt")
            break

    # answerable-from-source check (keyword evidence) when sources exist
    if source_texts:
        blob = " ".join(source_texts).lower()
        words = [w for w in _WORDS.findall(q.question.lower()) if len(w) > 4][:12]
        if words:
            evidence = sum(1 for w in words if w in blob) / len(words)
            if evidence < 0.18 and not q.source_reference:
                issues.append("not_answerable_from_source")
    return ValidationReport(valid=not issues, issues=issues)