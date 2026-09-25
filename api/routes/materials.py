"""
Course Materials Ingestion & Management Routes
"""
import os
import tempfile
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from api.dependencies import get_ai_service, get_current_student_id
from api.schemas import MaterialsListResponse, MaterialModel, MaterialUploadResponse
from src.integration.service import LearningIntelligenceModule

router = APIRouter(prefix="/materials", tags=["Course Materials"])


@router.get("", response_model=MaterialsListResponse)
def list_materials(
    student_id: Optional[str] = Query(None),
    course: Optional[str] = Query(None),
    current_student_id: str = Depends(get_current_student_id),
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """List all course materials uploaded for the student."""
    sid = student_id or current_student_id
    materials_raw = ai.list_course_materials(student_id=sid, course=course) or []

    models = [
        MaterialModel(
            document_id=getattr(m, "document_id", str(m)),
            filename=getattr(m, "filename", getattr(m, "name", "document")),
            course=getattr(m, "course", course or "General"),
            upload_date=getattr(m, "upload_date", None),
            status="indexed",
            chunk_count=getattr(m, "chunk_count", 1),
            source_type="student_upload",
        )
        for m in materials_raw
    ]
    return MaterialsListResponse(materials=models)


@router.post("/upload", response_model=MaterialUploadResponse)
async def upload_material(
    file: UploadFile = File(...),
    course: str = Form("General"),
    student_id: Optional[str] = Form(None),
    current_student_id: str = Depends(get_current_student_id),
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """
    Upload and index a course document (.txt, .md, .pdf, .docx, .pptx).
    Extracts text, generates embeddings, and indexes chunks into Chroma vector store.
    """
    sid = student_id or current_student_id
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing from upload.")

    # Write file content to a temporary file for ingestion
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        doc = ai.upload_course_material(
            student_id=sid,
            file_path=tmp_path,
            filename=file.filename,
            course=course,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(exc)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    return MaterialUploadResponse(
        document_id=getattr(doc, "document_id", "uploaded-doc"),
        filename=file.filename,
        course=course,
        chunk_count=getattr(doc, "chunk_count", 1),
        status="indexed",
        message="Material successfully uploaded and indexed into knowledge base.",
    )
