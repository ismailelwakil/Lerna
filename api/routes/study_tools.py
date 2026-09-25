"""
Study Tools / Content Generation Routes
"""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_ai_service, get_current_student_id
from api.schemas import (
    StudyToolsGenerateRequest,
    StudyToolsGenerateResponse,
    GeneratedResourceModel,
)
from src.integration.service import LearningIntelligenceModule

router = APIRouter(prefix="/study-tools", tags=["Study Tools"])


@router.post("/generate", response_model=StudyToolsGenerateResponse)
def generate_study_tools(
    body: StudyToolsGenerateRequest,
    current_student_id: str = Depends(get_current_student_id),
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """
    Generate one or multiple personalized study tools from the 15 supported kinds:
    [explanation, summary, notes, study_guide, flashcards, quiz, exam, practice,
     code, coding_exercise, diagram, presentation, analogy, comparison, question_bank].
    - Grounded strictly in uploaded materials or trusted external evidence.
    - Zero model-memory fallback for unavailable evidence.
    - Supports SVG preview + PPTX download artifacts.
    """
    sid = body.student_id or current_student_id
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required.")

    if not body.kinds or len(body.kinds) == 0:
        raise HTTPException(status_code=400, detail="At least one study tool kind must be requested.")

    doc_ids = body.document_ids if (body.document_ids and len(body.document_ids) > 0) else None

    try:
        out, _ = ai.generate_learning_resources(
            student_id=sid,
            topic=topic,
            kinds=body.kinds,
            language=body.language or "en",
            document_ids=doc_ids,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(exc)}")

    results: dict[str, GeneratedResourceModel] = {}

    for kind in body.kinds:
        raw = out.get(kind, {})
        res_type = raw.get("type", "unavailable")
        content = raw.get("content")
        raw_path = raw.get("path")
        filename = None
        download_url = None
        mime_type = None

        if raw_path:
            p = Path(raw_path)
            filename = p.name
            download_url = f"/artifacts/{filename}/download"
            if filename.endswith(".svg"):
                mime_type = "image/svg+xml"
                # If content is empty for svg, read content for preview
                if not content and p.exists():
                    try:
                        content = p.read_text(encoding="utf-8")
                    except Exception:
                        pass
            elif filename.endswith(".pptx"):
                mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

        results[kind] = GeneratedResourceModel(
            type=res_type,
            kind=kind,
            content=content,
            path=raw_path,
            filename=filename,
            download_url=download_url,
            mime_type=mime_type,
            sources=raw.get("sources", []),
            source_type=raw.get("source_type", "trusted_external" if not doc_ids else "student_upload"),
            learner_state=raw.get("learner_state"),
            teaching_strategy=raw.get("strategy"),
            evidence_limitation=raw.get("evidence_limitation"),
            message=raw.get("message"),
        )

    return StudyToolsGenerateResponse(topic=topic, resources=results)
