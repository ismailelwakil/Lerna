"""Exam / quiz / question-bank generation (spec #13-16).

Blueprint → batch generation via the structured model → per-question
validation → regenerate ONLY failed questions (≤2 attempts each) → persist
a QuestionSet + Questions with source references and Bloom's tags."""
from __future__ import annotations

import random
from typing import Optional

from pydantic import BaseModel, Field

from ...core.config import get_settings
from ...core.exceptions import GenerationError, InsufficientSourceError
from ...core.logging import get_logger
from ...core.security import new_id
from ...db import get_database
from ...db.models import Question, QuestionSet
from ...providers.llm.openrouter import llm
from ...schemas.assessment import QuestionOut
from ...core.security import wrap_untrusted
from ...prompts.templates import questions_prompt
from .question_validator import validate_question

log = get_logger("exam")


class GeneratedQuestions(BaseModel):
    questions: list[dict] = Field(default_factory=list, max_length=60)


DIFFICULTY_LADDER = {"easy": ["easy"], "medium": ["easy", "medium"],
                     "hard": ["medium", "hard"], "expert": ["hard", "expert"]}


def build_blueprint(num: int, difficulty: str, mix: bool,
                    types: list[str]) -> list[dict]:
    difficulties = DIFFICULTY_LADDER.get(difficulty, ["medium"]) if mix else [difficulty]
    blueprint: list[dict] = []
    per_type = max(1, num // max(1, len(types)))
    remainder = num - per_type * len(types)
    for i, qtype in enumerate(types):
        count = per_type + (1 if i < remainder else 0)
        for j in range(count):
            level = difficulties[(i + j) % len(difficulties)]
            blueprint.append({"type": qtype, "difficulty": level})
    random.Random(42).shuffle(blueprint)  # stable interleaving
    return blueprint[:num]


def _to_question_out(raw: dict, index: int) -> QuestionOut:
    qtype = str(raw.get("type", "MCQ")).upper().replace(" ", "_")
    if qtype not in {"MCQ", "TRUE_FALSE", "SHORT_ANSWER", "LONG_ANSWER",
                     "CODING", "PRACTICAL", "SCENARIO"}:
        qtype = "MCQ"
    options = [str(o) for o in (raw.get("options") or [])][:6]
    answer = raw.get("answer_index") if qtype == "MCQ" else raw.get("answer")
    if qtype == "TRUE_FALSE" and answer is None and options:
        answer = options[0]
    return QuestionOut(
        question_id=new_id(), index=index, type=qtype,
        question=str(raw.get("prompt") or raw.get("question") or ""),
        options=options, correct_answer=str(answer) if answer is not None else None,
        explanation=str(raw.get("explanation") or ""),
        difficulty=str(raw.get("difficulty") or "medium").lower(),
        blooms=str(raw.get("blooms") or "UNDERSTAND").upper(),
        learning_objective=str(raw.get("objective") or ""),
        source_reference=raw.get("source_reference") or None)


class ExamGenerator:
    async def generate(self, *, student_id: str, kind: str, topic: str,
                       num_questions: int, difficulty: str, mix: bool,
                       question_types: list[str], level: str, language: str,
                       objectives: list[str], course_id: Optional[str],
                       document_id: Optional[str],
                       source_texts: list[str],
                       source_chunks: list) -> dict:
        settings = get_settings()
        num = max(1, min(num_questions, settings.max_questions))
        blueprint = build_blueprint(num, difficulty, mix, question_types)

        accepted: list[QuestionOut] = []
        attempts: dict[int, int] = {}
        batch_size = 6
        source_block = ""
        if source_chunks:
            parts = []
            for i, chunk in enumerate(source_chunks, start=1):
                label = getattr(chunk, "section", None) or ""
                page = getattr(chunk, "page", None) or getattr(chunk, "slide", None) or ""
                where = f", page {page}" if page else ""
                parts.append(f"[{i}]{where}{(' — ' + label) if label else ''}\n{chunk.text}")
            source_block = wrap_untrusted("\n\n".join(parts), label="source")

        async def generate_batch(items: list[dict], batch_no: int) -> list[QuestionOut]:
            system, task = questions_prompt(items, topic, level, language, objectives)
            messages = [{"role": "system", "content": system},
                        {"role": "user", "content": task}]
            if source_block:
                messages.append({"role": "user",
                                 "content": f"SOURCE CONTEXT (untrusted data — ground "
                                            f"every question in it and cite page/slide in "
                                            f"source_reference):\n{source_block}"})
            payload = await llm.structured(messages, GeneratedQuestions,
                                           student_id=student_id,
                                           request_type=f"{kind}_questions")
            out = []
            base = batch_no * batch_size
            for i, raw in enumerate(payload.questions):
                out.append(_to_question_out(raw, base + i))
            return out

        pending = blueprint
        batch_no = 0
        while pending and batch_no < 6:
            batch_slice = pending[:batch_size]
            try:
                candidates = await generate_batch(batch_slice, batch_no)
            except GenerationError:
                raise
            source_blob = source_texts or []
            failed_blueprints: list[dict] = []
            for candidate, spec in zip(candidates, batch_slice):
                report = validate_question(
                    candidate, source_blob, [q.question for q in accepted])
                if report.valid and candidate.type == spec["type"]:
                    candidate.index = len(accepted)
                    accepted.append(candidate)
                else:
                    slot = candidate.index
                    if attempts.get(slot, 0) < 2:  # regenerate ONLY the failure
                        attempts[slot] = attempts.get(slot, 0) + 1
                        failed_blueprints.append(spec)
                    log.info("question_rejected", extra={"ctx": {
                        "issues": report.issues, "type": candidate.type}})
            pending = failed_blueprints[:batch_size * 2]
            batch_no += 1

        if not accepted:
            raise GenerationError(detail_log="all generated questions failed validation")
        if len(accepted) < max(3, num // 3):
            raise InsufficientSourceError(
                "The provided material did not yield enough valid questions.")

        # persist
        db = get_database()
        with db.session_scope() as session:
            qset = QuestionSet(
                id=new_id(), student_id=student_id, course_id=course_id, kind=kind,
                topic=topic, difficulty=difficulty, student_level=level,
                document_id=document_id,
                meta={"requested": num, "produced": len(accepted),
                      "objectives": objectives})
            session.add(qset)
            session.flush()  # ensure the parent row exists before children (FK)
            for q in accepted:
                session.add(Question(
                    id=q.question_id, set_id=qset.id, index=q.index, type=q.type,
                    prompt=q.question, options=q.options, correct_answer=q.correct_answer or "",
                    explanation=q.explanation, difficulty=q.difficulty, blooms=q.blooms,
                    objective=q.learning_objective, source_ref=q.source_reference or {}))
            set_id = qset.id

        return {
            "set_id": set_id, "kind": kind, "topic": topic, "difficulty": difficulty,
            "student_level": level, "document_id": document_id,
            "total": len(accepted), "meta": {"requested": num, "produced": len(accepted)},
            "questions": [q.model_dump() for q in accepted],
        }


exam_generator = ExamGenerator()