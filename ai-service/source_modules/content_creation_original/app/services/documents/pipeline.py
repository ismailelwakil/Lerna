"""Document upload pipeline job (spec #10): scan → extract → normalize →
chunk → embed → vector-index, with live status updates on the job."""
from __future__ import annotations

from ...core.logging import get_logger
from ...core.security import new_id
from ...db import get_database
from ...db.models import DocumentChunk, GenerationJob, UploadedDocument
from ...services.documents import processor
from ...services.rag.rag_service import rag

log = get_logger("doc-pipeline")


async def process_document_job(job_id: str, params: dict) -> None:
    db = get_database()
    with db.session_scope() as session:
        job = session.get(GenerationJob, job_id)
        if job is None:
            return
        document_id = job.params.get("document_id")
        # Guard: never call session.get() with a missing/None id — SQLAlchemy
        # emits "fully NULL primary key identity" SAWarning and behavior is
        # undefined. Malformed jobs fail safely instead.
        if not document_id or not isinstance(document_id, str):
            job.status, job.error = "FAILED", (
                "job params are missing a valid document_id")
            return
        doc = session.get(UploadedDocument, document_id)
        if doc is None:
            job.status, job.error = "FAILED", "document not found"
            return
        # TRUSTED OWNERSHIP: job params are client-supplied; the worker must
        # never let one student process another student's document.
        if doc.student_id != job.student_id:
            job.status, job.error = "FAILED", (
                "document does not belong to the job owner")
            log.warning("job_document_ownership_denied", extra={"ctx": {
                "job": job_id, "document": str(document_id)[:16]}})
            return
        student_id, storage_key, ext = doc.student_id, doc.storage_key, doc.ext
        doc.status = "processing"
        job.status, job.progress = "PROCESSING", 10

    from ...providers.storage.storage import storage
    content = await storage.get(storage_key)

    from ...services.documents.processor import build_scanner
    active_scanner = build_scanner()
    if active_scanner is None:
        # scanning REQUIRED but no scanner configured → fail safely
        # (document rejected; never silently treated as clean).
        with db.session_scope() as session:
            job = session.get(GenerationJob, job_id)
            doc = session.get(UploadedDocument, document_id)
            if job:
                job.status, job.error = "FAILED", (
                    "malware scanning is required but no scanner is configured "
                    "(set MALWARE_SCANNER=clamav)")
            if doc:
                doc.status, doc.error = "failed", "scanning required but unavailable"
        return

    clean, note = active_scanner.scan(content, ext)
    if not clean:
        with db.session_scope() as session:
            job = session.get(GenerationJob, job_id)
            doc = session.get(UploadedDocument, document_id)
            job.status, job.error = "FAILED", "malware-scan rejected the file"
            doc.status = "failed"
            doc.error = note
        # never leave rejected (possibly infected) material in storage
        try:
            from ...providers.storage.storage import storage as _storage
            await _storage.delete(storage_key)
        except Exception as exc:  # noqa: BLE001 — best-effort cleanup, logged
            log.warning("scan_reject_cleanup_failed",
                        extra={"ctx": {"err": str(exc)[:120]}})
        return

    with db.session_scope() as session:
        job = session.get(GenerationJob, job_id)
        job.progress = 30

    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        result = await processor.extract_image(content, f"image/{ext[1:]}")
    else:
        result = processor.process(content, ext)

    chunk_chars = params.get("chunk_chars", 1200)
    chunks: list[DocumentChunk] = []
    with db.session_scope() as session:
        existing = session.query(DocumentChunk).filter_by(document_id=document_id).count()
        if existing:  # idempotent reprocess
            session.query(DocumentChunk).filter_by(document_id=document_id).delete()
        for index, chunk in enumerate(result.chunks):
            if chunk_chars != 1200:
                pieces = processor._chunk(chunk.text, page=chunk.page, slide=chunk.slide,
                                          section=chunk.section, size=chunk_chars)
                for piece in pieces:
                    chunks.append(DocumentChunk(
                        id=new_id(), document_id=document_id, student_id=student_id,
                        chunk_index=len(chunks), text=piece.text, page=piece.page,
                        slide=piece.slide, section=piece.section))
            else:
                chunks.append(DocumentChunk(
                    id=new_id(), document_id=document_id, student_id=student_id,
                    chunk_index=index, text=chunk.text, page=chunk.page,
                    slide=chunk.slide, section=chunk.section))
        session.add_all(chunks)
        doc_row = session.get(UploadedDocument, document_id)
        doc_row.status, doc_row.page_count = "processed", result.pages or result.slides
        doc_row.doc_meta.update({"meta": result.meta,
                                 "language": processor.detect_language(result.chunks),
                                 "chunk_count": len(chunks)})
        job = session.get(GenerationJob, job_id)
        job.progress = 60

    indexed = await rag.index_chunks(chunks) if chunks else 0
    with db.session_scope() as session:
        job = session.get(GenerationJob, job_id)
        job.status, job.progress = "COMPLETED", 100
        job.result = {"document_id": document_id, "chunks": len(chunks),
                      "indexed": indexed, "pages": result.pages or result.slides,
                      "meta": result.meta}
    log.info("document_processed", extra={"ctx": {
        "document_id": document_id, "chunks": len(chunks), "indexed": indexed}})