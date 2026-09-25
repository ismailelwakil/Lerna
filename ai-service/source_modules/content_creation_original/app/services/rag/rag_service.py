"""RAG service (spec #17-19): embed → vector store → grounded retrieval with
source references. Retrieved text is ALWAYS wrapped as untrusted data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ...core.logging import get_logger
from ...core.security import wrap_untrusted
from ...db import get_database
from ...db.models import DocumentChunk, UploadedDocument
from ...providers.vector.qdrant import vector_store

log = get_logger("rag")


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str
    page: Optional[int]
    slide: Optional[int]
    section: Optional[str]
    score: float

    def reference(self) -> dict:
        ref = {"document_id": self.document_id}
        if self.page:
            ref["page"] = self.page
        if self.slide:
            ref["slide"] = self.slide
        return ref

    def source_label(self) -> str:
        from ...db import get_database
        db = get_database()
        with db.session_scope() as session:
            doc = session.get(UploadedDocument, self.document_id)
            name = doc.filename if doc else self.document_id[:8]
        where = f", page {self.page}" if self.page else (
            f", slide {self.slide}" if self.slide else "")
        return f"{name}{where}"


class RAGService:
    def __init__(self) -> None:
        self._embedder = None

    async def _embed(self, texts: list[str]) -> tuple[list[list[float]], str, int]:
        if self._embedder is None:
            from ...providers.image.gemini_media import GeminiEmbedding
            self._embedder = GeminiEmbedding()
        return await self._embedder.embed(texts)

    # ------------------------------------------------------------- index
    async def index_chunks(self, chunks: list[DocumentChunk]) -> int:
        if not chunks:
            return 0
        texts = [c.text for c in chunks]
        vectors, provider, dim = await self._embed(texts)
        await vector_store.upsert(
            ids=[c.id for c in chunks], vectors=vectors,
            payloads=[{
                "document_id": c.document_id, "student_id": c.student_id,
                "chunk_index": c.chunk_index, "text": c.text[:2000],
                "page": c.page, "slide": c.slide, "section": c.section,
                "embedding_provider": provider} for c in chunks])
        db = get_database()
        with db.session_scope() as session:
            for chunk in chunks:
                stored = session.get(DocumentChunk, chunk.id)
                if stored:
                    stored.indexed = True
        log.info("rag_indexed", extra={"ctx": {"chunks": len(chunks),
                                               "provider": provider, "dim": dim}})
        return len(chunks)

    # ---------------------------------------------------------- retrieve
    async def retrieve(self, student_id: str, query: str, *,
                       document_ids: Optional[list[str]] = None,
                       k: int = 6) -> list[RetrievedChunk]:
        vectors, _, _ = await self._embed([query])
        query_vector = vectors[0]
        hits: list = []
        if document_ids:
            for document_id in document_ids:
                hits += await vector_store.search(
                    query_vector, k=k, filter_student=student_id,
                    filter_document=document_id)
        else:
            hits = await vector_store.search(query_vector, k=k,
                                             filter_student=student_id)
        hits.sort(key=lambda h: -h.score)
        results: list[RetrievedChunk] = []
        for hit in hits[:k]:
            payload = hit.payload
            results.append(RetrievedChunk(
                chunk_id=payload.get("chunk_id", ""), document_id=payload["document_id"],
                text=payload.get("text", ""), page=payload.get("page"),
                slide=payload.get("slide"), section=payload.get("section"),
                score=round(hit.score, 4)))
        return results

    @staticmethod
    def context_block(chunks: list[RetrievedChunk]) -> str:
        """Untrusted, labeled source context for prompts."""
        if not chunks:
            return ""
        parts = []
        for i, chunk in enumerate(chunks, start=1):
            header = f"[{i}] {chunk.source_label()}"
            if chunk.section:
                header += f" — {chunk.section}"
            parts.append(f"{header}\n{chunk.text}")
        return wrap_untrusted("\n\n".join(parts), label="source")

    async def delete_document(self, document_id: str) -> None:
        await vector_store.delete_document(document_id)


rag = RAGService()