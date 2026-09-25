"""
Diagnostic Assessment & Knowledge Check Routes
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_ai_service, get_current_student_id
from api.schemas import (
    AssessmentGenerateRequest,
    AssessmentGenerateResponse,
    AssessmentQuestionModel,
    AssessmentSubmitRequest,
    AssessmentSubmitResponse,
)
from src.integration.service import LearningIntelligenceModule

router = APIRouter(prefix="/assessments", tags=["Assessments & Knowledge Checks"])

# In-memory session store for active diagnostic assessments awaiting submission
_ACTIVE_ASSESSMENTS: Dict[str, Any] = {}


@router.post("/generate", response_model=AssessmentGenerateResponse)
def generate_assessment(
    body: AssessmentGenerateRequest,
    current_student_id: str = Depends(get_current_student_id),
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """
    Generate an assessment / diagnostic knowledge check.
    - Grounded in uploaded material or trusted external evidence.
    - Questions contain MCQs and short answers with an explicit 'I don't know' option.
    - Stored in server cache until submitted.
    """
    sid = body.student_id or current_student_id
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required.")

    doc_ids = body.document_ids if (body.document_ids and len(body.document_ids) > 0) else None

    try:
        diag = ai.create_diagnostic(
            student_id=sid,
            topic=topic,
            language=body.language or "en",
            document_ids=doc_ids,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate assessment: {str(exc)}")

    # Store for submission lookup
    _ACTIVE_ASSESSMENTS[diag.assessment_id] = diag

    questions_out: list[AssessmentQuestionModel] = []
    for q in diag.questions:
        questions_out.append(
            AssessmentQuestionModel(
                question_id=q.question_id,
                concept=getattr(q, "concept", topic),
                kind=getattr(q, "kind", "mcq"),
                prompt=getattr(q, "prompt", ""),
                options=getattr(q, "options", []) or [],
                difficulty=getattr(q, "difficulty", "medium"),
                source_type=getattr(q, "source_type", getattr(diag, "source_type", "trusted_external")),
                source_title=getattr(q, "source_title", getattr(diag, "source_title", "Course Evidence")),
            )
        )

    return AssessmentGenerateResponse(
        assessment_id=diag.assessment_id,
        topic=diag.topic,
        questions=questions_out,
        source_type=getattr(diag, "source_type", "trusted_external"),
        source_title=getattr(diag, "source_title", "Course Evidence"),
    )


@router.post("/{assessment_id}/submit", response_model=AssessmentSubmitResponse)
def submit_assessment(
    assessment_id: str,
    body: AssessmentSubmitRequest,
    current_student_id: str = Depends(get_current_student_id),
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """
    Submit completed answers for evaluation.
    - Backend evaluates correctness and updates student mastery.
    - React does NOT evaluate or update mastery client-side.
    """
    sid = body.student_id or current_student_id
    diag = _ACTIVE_ASSESSMENTS.get(assessment_id)
    if not diag:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment session '{assessment_id}' not found or already submitted. Please generate a new check.",
        )

    try:
        result = ai.submit_diagnostic(
            student_id=sid,
            assessment=diag,
            answers=body.answers,
            language=body.language or "en",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Assessment evaluation failed: {str(exc)}")
    finally:
        # Clear completed assessment session
        _ACTIVE_ASSESSMENTS.pop(assessment_id, None)

    # Build per-question feedback for the student
    feedback: Dict[str, Any] = {}
    for q in getattr(diag, "questions", []):
        student_ans = body.answers.get(q.question_id, "")
        expected = getattr(q, "expected", "")
        is_idk = student_ans.strip().lower() in ("i don't know", "idk")
        is_correct = (student_ans.strip().lower() == expected.strip().lower()) and not is_idk
        feedback[q.question_id] = {
            "concept": getattr(q, "concept", ""),
            "student_answer": student_ans,
            "expected_answer": expected,
            "is_correct": is_correct,
            "is_idk": is_idk,
            "rubric": getattr(q, "rubric", ""),
        }

    return AssessmentSubmitResponse(
        assessment_id=getattr(result, "assessment_id", assessment_id),
        score=float(getattr(result, "score", 0.0)),
        concept_mastery=getattr(result, "concept_mastery", {}) or {},
        weak_concepts=getattr(result, "weak_concepts", []) or [],
        unknown_concepts=getattr(result, "unknown_concepts", []) or [],
        strengths=getattr(result, "strengths", []) or [],
        recommendations=getattr(result, "recommendations", []) or [],
        feedback_per_question=feedback,
    )
