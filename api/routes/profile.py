"""
Student Profile & Learning State Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_ai_service, get_current_student_id
from api.schemas import (
    StudentProfileData,
    StudentPreferencesUpdate,
    LearningStateResponse,
    NextBestActionData,
    StudyPlanItem,
    SpacedReviewItem,
)
from src.integration.service import LearningIntelligenceModule

router = APIRouter(prefix="/students", tags=["Student Profile & Learning"])


@router.get("/{student_id}/profile", response_model=StudentProfileData)
def get_profile(
    student_id: str,
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """Retrieve the current student profile and concept mastery."""
    p = ai.get_learning_profile(student_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Student profile '{student_id}' not found")

    student = getattr(p, "student", None)
    return StudentProfileData(
        student_id=getattr(student, "student_id", student_id),
        name=getattr(student, "name", "Student"),
        course=getattr(student, "course", "General"),
        preferred_language=getattr(student, "preferred_language", "en"),
        learning_preference=getattr(student, "learning_preference", "step-by-step"),
        concept_mastery=getattr(p, "concept_mastery", {}) or {},
        weak_concepts=getattr(p, "weak_concepts", []) or [],
        unknown_concepts=getattr(p, "unknown_concepts", []) or [],
        strengths=getattr(p, "strengths", []) or [],
        misconceptions=getattr(p, "misconceptions", []) or [],
        prerequisite_gaps=getattr(p, "prerequisite_gaps", []) or [],
        recent_topics=getattr(p, "recent_topics", []) or [],
    )


@router.patch("/{student_id}/preferences", response_model=StudentProfileData)
def update_preferences(
    student_id: str,
    body: StudentPreferencesUpdate,
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """Update student learning preferences, course, or preferred language."""
    curr = ai.get_learning_profile(student_id)
    curr_student = getattr(curr, "student", None) if curr else None
    name = body.name or (getattr(curr_student, "name", "Student") if curr_student else "Student")
    course = body.course or (getattr(curr_student, "course", "General") if curr_student else "General")
    lang = body.preferred_language or (getattr(curr_student, "preferred_language", "en") if curr_student else "en")
    pref = body.learning_preference or (getattr(curr_student, "learning_preference", "step-by-step") if curr_student else "step-by-step")

    p = ai.sync_learning_context(
        student_id=student_id,
        name=name,
        course=course,
        language=lang,
        learning_preference=pref,
    )

    student = getattr(p, "student", None)
    return StudentProfileData(
        student_id=getattr(student, "student_id", student_id),
        name=getattr(student, "name", name),
        course=getattr(student, "course", course),
        preferred_language=getattr(student, "preferred_language", lang),
        learning_preference=getattr(student, "learning_preference", pref),
        concept_mastery=getattr(p, "concept_mastery", {}) or {},
        weak_concepts=getattr(p, "weak_concepts", []) or [],
        unknown_concepts=getattr(p, "unknown_concepts", []) or [],
        strengths=getattr(p, "strengths", []) or [],
        misconceptions=getattr(p, "misconceptions", []) or [],
        prerequisite_gaps=getattr(p, "prerequisite_gaps", []) or [],
        recent_topics=getattr(p, "recent_topics", []) or [],
    )


@router.get("/{student_id}/learning", response_model=LearningStateResponse)
def get_learning_state(
    student_id: str,
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """
    Get aggregated learning state including Next Best Action,
    personalized study plan, spaced repetition queue, and activity history.
    """
    p = ai.get_learning_profile(student_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Student profile '{student_id}' not found")

    student = getattr(p, "student", None)
    profile_data = StudentProfileData(
        student_id=getattr(student, "student_id", student_id),
        name=getattr(student, "name", "Student"),
        course=getattr(student, "course", "General"),
        preferred_language=getattr(student, "preferred_language", "en"),
        learning_preference=getattr(student, "learning_preference", "step-by-step"),
        concept_mastery=getattr(p, "concept_mastery", {}) or {},
        weak_concepts=getattr(p, "weak_concepts", []) or [],
        unknown_concepts=getattr(p, "unknown_concepts", []) or [],
        strengths=getattr(p, "strengths", []) or [],
        misconceptions=getattr(p, "misconceptions", []) or [],
        prerequisite_gaps=getattr(p, "prerequisite_gaps", []) or [],
        recent_topics=getattr(p, "recent_topics", []) or [],
    )

    nba_obj = ai.get_next_learning_action(student_id)
    next_action = None
    if nba_obj:
        next_action = NextBestActionData(
            action=getattr(nba_obj, "action", ""),
            reason=getattr(nba_obj, "reason", ""),
            target_concepts=getattr(nba_obj, "target_concepts", []) or [],
            strategy=getattr(nba_obj, "strategy", ""),
            recommended_resources=getattr(nba_obj, "recommended_resources", []) or [],
            priority=getattr(nba_obj, "priority", "medium"),
            triggering_evidence=getattr(nba_obj, "triggering_evidence", None),
        )

    study_plan_raw = ai.get_study_plan(student_id) or []
    study_plan = [
        StudyPlanItem(
            title=item.get("title", ""),
            concept=item.get("concept", ""),
            priority=item.get("priority", "medium"),
            reason=item.get("reason", ""),
            recommended_actions=item.get("recommended_actions", []),
            completed=item.get("completed", False),
        )
        for item in study_plan_raw
        if isinstance(item, dict)
    ]

    review_queue_raw = ai.get_review_queue(student_id) or []
    review_queue = [
        SpacedReviewItem(
            concept=item.get("concept", ""),
            due_date=str(item.get("due_date", "")),
            interval_days=float(item.get("interval_days", 1.0)),
            repetition=int(item.get("repetition", 0)),
            ease_factor=float(item.get("ease_factor", 2.5)),
            last_reviewed=str(item.get("last_reviewed")) if item.get("last_reviewed") else None,
            mastery=float(item.get("mastery", 0.0)),
        )
        for item in review_queue_raw
        if isinstance(item, dict)
    ]

    learning_history = getattr(p, "learning_history", []) or []

    return LearningStateResponse(
        profile=profile_data,
        next_action=next_action,
        study_plan=study_plan,
        review_queue=review_queue,
        learning_history=learning_history[-15:],  # Return recent items
    )
