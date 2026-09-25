"""
Spaced Repetition Review Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_ai_service, get_current_student_id
from api.schemas import SpacedReviewRequest, SpacedReviewResponse
from src.integration.service import LearningIntelligenceModule

router = APIRouter(prefix="/spaced-repetition", tags=["Spaced Repetition"])


@router.post("/review", response_model=SpacedReviewResponse)
def record_review(
    body: SpacedReviewRequest,
    current_student_id: str = Depends(get_current_student_id),
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """
    Record student spaced repetition review feedback ('Remembered' or 'Forgot').
    Updates Leitner/SM-2 intervals and profile persistence server-side.
    """
    sid = body.student_id or current_student_id
    concept = body.concept.strip()
    if not concept:
        raise HTTPException(status_code=400, detail="Concept is required.")

    try:
        res = ai.record_concept_review(
            student_id=sid,
            concept=concept,
            remembered=body.remembered,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to record review: {str(exc)}")

    return SpacedReviewResponse(
        success=True,
        concept=concept,
        remembered=body.remembered,
        next_review_date=str(res.get("due_date")) if isinstance(res, dict) and res.get("due_date") else None,
        interval_days=float(res.get("interval_days", 1.0)) if isinstance(res, dict) else None,
        mastery=float(res.get("mastery", 0.0)) if isinstance(res, dict) else None,
    )
