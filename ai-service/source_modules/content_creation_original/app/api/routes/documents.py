"""Document routes — secure upload, processing job, listing, deletion."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, UploadFile

from ...core.exceptions import FileTooLargeError
from ...core.logging import get_logger
from ...core.security import new_id, validate_upload
from ...db import get_database
from ...db.models import DocumentChunk, UploadedDocument
from ...providers.storage.storage import storage
from ...schemas.documents import DocumentOut, ProcessRequest
from ...services.telemetry import telemetry
from ..dependencies import audit, rate, student_identity

log = get_logger("api.docs")
router = APIRouter(prefix="/documents")


def _out(doc: UploadedDocument, chunks: int = 0) -> dict:
    return DocumentOut(document_id=doc.id, filename=doc.filename, ext=doc.ext,
                       size_bytes=doc.size_bytes, status=doc.status,
                       page_count=doc.page_count, chunks=chunks,
                       created_at=doc.created_at.isoformat(),
                       meta=doc.doc_meta or {}).model_dump()


UPLOAD_CHUNK = 1024 * 1024  # 1 MiB bounded reads


async def read_bounded(file: UploadFile, max_bytes: int) -> bytes:
    """Read at most max_bytes+1 in bounded chunks — an attacker can never
    force unbounded memory allocation (oversize is detected on the FIRST
    chunk that crosses the limit)."""
    buffer = bytearray()
    while True:
        chunk = await file.read(UPLOAD_CHUNK)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise FileTooLargeError(
                f"File exceeds the {max_bytes // (1024 * 1024)} MB limit.")
    return bytes(buffer)


@router.post("/upload", dependencies=[Depends(rate("upload"))])
async def upload_file(
    file: UploadFile = File(...),
    student_id: str = Depends(student_identity),
    x_course_id: str = Header(default=""),
):
    from ...core.config import get_settings as _gs
    content = await read_bounded(file, _gs().max_upload_mb * 1024 * 1024)
    stem, ext = validate_upload(file.filename or "", content,
                                file.content_type or "")
    from ...core.security import ALLOWED_EXTENSIONS
    key = storage.new_key(student_id, ext)
    await storage.put(key, content,
                      mime=ALLOWED_EXTENSIONS.get(ext, "application/octet-stream"))
    db = get_database()
    with db.session_scope() as session:
        doc = UploadedDocument(
            id=new_id(), student_id=student_id,
            course_id=x_course_id or None, filename=f"{stem}{ext}", ext=ext,
            size_bytes=len(content), storage_key=key, status="uploaded")
        session.add(doc)
        document = doc
    telemetry.record_provider(student_id=student_id, provider="storage",
                              model=storage.backend, request_type="upload",
                              est_cost_usd=0.0)
    audit("upload", student_id=student_id, ext=ext, size=len(content))
    return _out(document)


@router.post("/{document_id}/process", dependencies=[Depends(rate("jobs"))])
async def process(document_id: str, payload: ProcessRequest,
                  student_id: str = Depends(student_identity)):
    from ...core.exceptions import NotFoundError
    from sqlalchemy import select
    db = get_database()
    with db.session_scope() as session:
        doc = session.scalar(
            select(UploadedDocument).where(UploadedDocument.id == document_id,
                                           UploadedDocument.student_id == student_id))
        if doc is None:
            raise NotFoundError("Document not found.")  # ownership-aware lookup
    from ...workers.worker import create_job, executor
    job = create_job(student_id=student_id, kind="document_process",
                     params={"document_id": document_id,
                             "chunk_chars": payload.chunk_chars,
                             "overlap": payload.overlap})
    await executor.submit(job.id, "document_process")
    return {"job_id": job.id, "status": "QUEUED", "document_id": document_id}


@router.get("", dependencies=[Depends(rate("default"))])
async def list_documents(student_id: str = Depends(student_identity)):
    db = get_database()
    with db.session_scope() as session:
        from sqlalchemy import select
        docs = list(session.scalars(
            select(UploadedDocument).where(
                UploadedDocument.student_id == student_id)
            .order_by(UploadedDocument.created_at.desc()).limit(100)))
        counts = {d.id: session.query(DocumentChunk)
                  .filter_by(document_id=d.id).count() for d in docs}
    return {"documents": [_out(d, counts.get(d.id, 0)) for d in docs]}


@router.get("/{document_id}", dependencies=[Depends(rate("default"))])
async def get_document(document_id: str,
                       student_id: str = Depends(student_identity)):
    from ...core.exceptions import NotFoundError
    from sqlalchemy import select
    db = get_database()
    with db.session_scope() as session:
        doc = session.scalar(
            select(UploadedDocument).where(UploadedDocument.id == document_id,
                                           UploadedDocument.student_id == student_id))
        if doc is None:
            raise NotFoundError("Document not found.")  # ownership-aware lookup
        chunks = session.query(DocumentChunk).filter_by(document_id=doc.id).count()
    return _out(doc, chunks)


@router.delete("/{document_id}", dependencies=[Depends(rate("default"))])
async def delete_document(document_id: str,
                          student_id: str = Depends(student_identity)):
    from ...core.exceptions import NotFoundError
    from sqlalchemy import select
    db = get_database()
    with db.session_scope() as session:
        doc = session.scalar(
            select(UploadedDocument).where(UploadedDocument.id == document_id,
                                           UploadedDocument.student_id == student_id))
        if doc is None:
            raise NotFoundError("Document not found.")  # ownership-aware lookup
        key = doc.storage_key
        session.delete(doc)
    await storage.delete(key)
    from ...services.rag.rag_service import rag
    await rag.delete_document(document_id)
    return {"deleted": True, "document_id": document_id}