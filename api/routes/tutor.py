"""
AI Tutor Chat & Voice Routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from api.dependencies import get_ai_service, get_current_student_id
from api.schemas import TutorChatRequest, TutorChatResponse, CitationModel
from src.integration.service import LearningIntelligenceModule

router = APIRouter(prefix="/tutor", tags=["AI Tutor"])


@router.post("/chat", response_model=TutorChatResponse)
def chat_with_tutor(
    body: TutorChatRequest,
    current_student_id: str = Depends(get_current_student_id),
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """
    Primary conversational learning endpoint.
    - If document_ids is null or empty: runs Trusted External Discovery (Mode B).
    - If document_ids has items: runs selected course material retrieval (Mode A).
    - Preserves hierarchical personalization, citations, and evidence limitations.
    """
    student_id = body.student_id or current_student_id
    course = body.course_id or "General"
    query_text = body.message.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query message cannot be empty")

    language = body.language or "en"
    doc_ids = body.document_ids if (body.document_ids and len(body.document_ids) > 0) else None

    # Style adaptation: append prompt hint if Socratic guidance is selected
    effective_query = query_text
    if body.tutoring_style == "socratic":
        effective_query = f"{query_text} (Please guide me socratically with thoughtful questions rather than giving away the complete solution immediately.)"

    try:
        response = ai.ask_tutor(
            student_id=student_id,
            course_id=course,
            text=effective_query,
            language=language,
            document_ids=doc_ids,
            session_id=body.session_id or "web-session",
            chat_history=body.chat_history or [],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI Tutor generation error: {str(exc)}")

    rendered_answer = response.answer
    if (
        response.evidence
        and not response.abstained
        and hasattr(ai, "tutor")
        and hasattr(ai.tutor, "validator")
    ):
        rendered_answer = ai.tutor.validator.validate_rendered_answer(
            rendered_answer,
            response.evidence,
            query=query_text,
        )

    # Convert citations
    citations: list[CitationModel] = []
    source_type = "student_upload" if doc_ids else "trusted_external"

    for i, ev in enumerate(response.evidence or []):
        citations.append(
            CitationModel(
                citation_id=f"cite-{i+1}",
                chunk_id=getattr(ev, "chunk_id", f"chunk-{i}"),
                source=getattr(ev, "source", "Authoritative Source"),
                source_type=getattr(ev, "source_type", source_type),
                authority=getattr(ev, "authority", "university"),
                trust_score=float(getattr(ev, "trust_score", 1.0)),
                url=getattr(ev, "url", getattr(ev, "source_url", None)),
                page=getattr(ev, "page", None),
                excerpt=getattr(ev, "text", "")[:300] if getattr(ev, "text", None) else None,
                title=getattr(ev, "source", "Course Evidence"),
            )
        )

    # Detect evidence limitation notice in answer
    limitation = None
    if "Evidence Limitation" in rendered_answer or "limitation notice" in rendered_answer.lower():
        limitation = "The retrieved evidence provides substantive support for the core concepts, but certain specific bounds or sub-facets were not explicitly present in the sources."

    return TutorChatResponse(
        answer=rendered_answer,
        evidence=citations,
        abstained=response.abstained,
        search_state=getattr(response, "trusted_search_state", getattr(response, "search_state", None)),
        source_type=source_type,
        evidence_limitation=limitation,
        diagnostics=getattr(response, "diagnostics", {}) or {},
    )


@router.post("/voice", response_model=TutorChatResponse)
async def voice_question(
    file: Optional[UploadFile] = File(None),
    student_id: Optional[str] = Form(None),
    course_id: Optional[str] = Form("General"),
    language: Optional[str] = Form("en"),
    current_student_id: str = Depends(get_current_student_id),
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """
    Voice Question integration boundary.
    Accepts uploaded audio bytes. If audio processing is active, routes to ask_voice_tutor;
    otherwise returns a clear safe message with capability status.
    """
    sid = student_id or current_student_id
    if not file:
        raise HTTPException(status_code=400, detail="Audio file is required for voice queries.")

    audio_bytes = await file.read()
    try:
        response = ai.ask_voice_tutor(
            student_id=sid,
            course_id=course_id or "General",
            audio_data=audio_bytes,
            language=language or "en",
        )
        return TutorChatResponse(
            answer=response.answer,
            evidence=[],
            abstained=response.abstained,
            search_state="voice_processed",
            source_type="trusted_external",
        )
    except Exception as exc:
        return TutorChatResponse(
            answer="Voice transcription is currently in preview mode. Please use the text input for complete source-grounded answers.",
            evidence=[],
            abstained=False,
            search_state="voice_pending",
            source_type="trusted_external",
            diagnostics={"voice_note": str(exc)},
        )
