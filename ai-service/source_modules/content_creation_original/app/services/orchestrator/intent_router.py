"""'From document' natural-language instruction service (spec #12) —
understands "Summarize this", "Create 20 MCQs", "Teach me this material", …
and dispatches to the right generator. Intent model with a rule-based fallback."""
from __future__ import annotations

import re

from pydantic import BaseModel

from ...core.exceptions import ValidationError
from ...core.logging import get_logger
from ...providers.llm.openrouter import llm
from ...prompts.templates import from_document_intent_prompt
from ...schemas.documents import FromDocumentRequest
from ...schemas.common import BaseContentRequest, LearnerContext, StudentLevel

log = get_logger("intent")

_RULES = [
    (re.compile(r"\b(summar\w*|tl;?dr|overview)", re.I), "summarize"),
    (re.compile(r"\b(flash ?cards?|بطاقات)\b", re.I), "flashcards"),
    (re.compile(r"\b(exam|test paper|اختبار شامل)\b", re.I), "exam"),
    (re.compile(r"\b(\d+\s*(mcq|multiple choice|question)|mcqs?|quiz|test me|اختبرني)\b", re.I), "quiz"),
    (re.compile(r"\b(study guide|دليل دراسة)\b", re.I), "study_guide"),
    (re.compile(r"\b(teach\w*|explain\w*|علمني|اشرح)", re.I), "explain"),
    (re.compile(r"\b(difficult|hard concepts|صعب)\b", re.I), "difficult_concepts"),
    (re.compile(r"\b(diagram|رسم)\b", re.I), "diagram"),
    (re.compile(r"\b(notes?|ملاحظات)\b", re.I), "notes"),
    (re.compile(r"\b(video|فيديو)\b", re.I), "video"),
    (re.compile(r"\b(read|audio|اقرأ|صوت)\b", re.I), "audio"),
]

_COUNT = re.compile(r"(\d{1,3})")


class Intent(BaseModel):
    intent: str
    count: int | None = None
    notes: str = ""


class IntentRouter:
    async def classify(self, instruction: str, student_id: str) -> Intent:
        rule_hit = None
        for pattern, intent in _RULES:
            if pattern.search(instruction):
                rule_hit = intent
                break
        count = None
        number = _COUNT.search(instruction)
        if number:
            count = max(1, min(50, int(number.group(1))))
        if llm.mode != "mock":
            try:
                system, task = from_document_intent_prompt(instruction, "beginner", "en")
                result = await llm.structured(
                    [{"role": "system", "content": system}, {"role": "user", "content": task}],
                    Intent, student_id=student_id, request_type="intent")
                if result.intent != "other":
                    result.count = result.count or count
                    return result
            except Exception as exc:  # noqa: BLE001 — rules are the fallback
                log.info("intent_llm_failed", extra={"ctx": {"err": str(exc)[:120]}})
        if rule_hit is None:
            raise ValidationError(
                "Could not determine what to do with the document. Try e.g. "
                "'Summarize this', 'Create 20 MCQs', 'Create flashcards', or "
                "'Teach me this material'.")
        return Intent(intent=rule_hit, count=count, notes="rule-based")

    def to_content_request(self, request: FromDocumentRequest, intent: Intent
                           ) -> BaseContentRequest:
        return BaseContentRequest(
            student_id=request.student_id, topic="uploaded material",
            document_ids=request.document_ids, inline_material=None,
            level=StudentLevel(request.level), language=request.language,
            allow_external_knowledge=request.allow_external_knowledge,
            learner=LearnerContext())


intent_router = IntentRouter()