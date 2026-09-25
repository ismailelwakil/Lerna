"""Assessment routes — quiz / exam / question-bank / practice, grounded in
the student's uploaded documents when provided."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...schemas.assessment import AssessmentRequest, BankFilter
from ...services.assessment.exam_generator import exam_generator
from ...services.rag.rag_service import rag
from ..dependencies import audit, authorize_student, quota_guard, rate, student_identity

router = APIRouter()


async def _generate(request: AssessmentRequest, kind: str,
                    student: str) -> dict:
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(request.student_id)
    chunks = []
    if request.document_ids:
        for document_id in request.document_ids:
            from ...services.orchestrator.orchestrator import orchestrator
            orchestrator.owned_document(request.student_id, document_id)
        chunks = await rag.retrieve(
            request.student_id, f"{request.topic} {request.learning_objectives}",
            document_ids=request.document_ids, k=8)
    if not chunks and not request.inline_material and not request.allow_external_knowledge \
            and request.topic == "uploaded material":
        from ...core.exceptions import InsufficientSourceError
        raise InsufficientSourceError()
    source_texts = [c.text for c in chunks] or (
        [request.inline_material] if request.inline_material else [])
    result = await exam_generator.generate(
        student_id=request.student_id, kind=kind, topic=request.topic,
        num_questions=request.num_questions, difficulty=request.difficulty.value,
        mix=request.mix_difficulty, question_types=request.question_types,
        level=str(request.level), language=request.language,
        objectives=request.learning_objectives, course_id=request.course_id,
        document_id=request.document_ids[0] if request.document_ids else None,
        source_texts=source_texts, source_chunks=chunks)
    audit("assessment", student_id=request.student_id, kind=kind,
          total=result["total"])
    if not request.include_answers:
        for question in result["questions"]:
            question.pop("correct_answer", None)
            question.pop("explanation", None)
    return result


@router.post("/quiz")
async def quiz(request: AssessmentRequest,
               student: str = Depends(student_identity),
               _rl: None = Depends(rate("expensive"))):
    return await _generate(request, "quiz", student)


@router.post("/exam")
async def exam(request: AssessmentRequest,
               student: str = Depends(student_identity),
               _rl: None = Depends(rate("expensive"))):
    return await _generate(request, "exam", student)


@router.post("/practice")
async def practice(request: AssessmentRequest,
                   student: str = Depends(student_identity),
                   _rl: None = Depends(rate("generate"))):
    return await _generate(request, "practice", student)


@router.post("/question-bank")
async def question_bank(request: AssessmentRequest,
                        student: str = Depends(student_identity),
                        _rl: None = Depends(rate("expensive"))):
    return await _generate(request, "question_bank", student)


@router.post("/question-bank/filter")
async def filter_bank(filter_: BankFilter,
                      student: str = Depends(student_identity),
                      _rl: None = Depends(rate("default"))):
    filter_.student_id = authorize_student(student, filter_.student_id)
    """Filter + randomize from the student's existing question sets. Answer
    keys are stripped unless explicitly requested (spec #16)."""
    import random as _random
    from ...db import get_database
    from ...db.models import Question, QuestionSet
    from ...core.exceptions import NotFoundError
    from sqlalchemy import select
    db = get_database()
    with db.session_scope() as session:
        stmt = select(QuestionSet).where(QuestionSet.student_id == filter_.student_id)
        if filter_.document_id:
            stmt = stmt.where(QuestionSet.document_id == filter_.document_id)
        sets = list(session.scalars(stmt))
        pool: list[Question] = []
        for qset in sets:
            if filter_.topic and filter_.topic.lower() not in qset.topic.lower():
                continue
            pool.extend(session.scalars(
                select(Question).where(Question.set_id == qset.id)))
        if filter_.difficulty:
            pool = [q for q in pool if q.difficulty == filter_.difficulty.value]
        if filter_.question_type:
            pool = [q for q in pool if q.type == filter_.question_type.upper()]
        if filter_.learning_objective:
            needle = filter_.learning_objective.lower()
            pool = [q for q in pool if needle in (q.objective or "").lower()]
        if filter_.randomize:
            _random.shuffle(pool)
        selected = pool[: filter_.limit]
    if not selected:
        raise NotFoundError("No stored questions match the filter.")
    questions = [{
        "question_id": q.id, "index": i, "type": q.type, "question": q.prompt,
        "options": q.options,
        **({"correct_answer": q.correct_answer, "explanation": q.explanation}
           if filter_.include_answers else {}),
        "difficulty": q.difficulty, "blooms": q.blooms,
        "learning_objective": q.objective, "source_reference": q.source_ref,
    } for i, q in enumerate(selected)]
    return {"total": len(questions), "questions": questions}