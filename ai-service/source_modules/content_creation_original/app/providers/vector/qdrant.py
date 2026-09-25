"""Vector stores — Qdrant (primary, REST) with in-memory fallback (spec #17)."""
from __future__ import annotations

import math
from typing import Optional

import httpx

from ...core.config import get_settings
from ...core.logging import get_logger
from ..base import ScoredPoint

log = get_logger("vector")


class QdrantStore:
    """Qdrant Cloud REST client — one collection per embedding dimension."""
    name = "qdrant"

    def __init__(self) -> None:
        s = get_settings()
        if not s.qdrant_url:
            raise ValueError("QDRANT_URL not set")
        self._client = httpx.AsyncClient(
            base_url=s.qdrant_url, headers={"api-key": s.qdrant_api_key},
            timeout=httpx.Timeout(30.0, connect=10.0))

    def _collection(self, dim: int) -> str:
        return f"edunation_content_{dim}"

    async def ensure_collection(self, dim: int) -> None:
        name = self._collection(dim)
        resp = await self._client.get(f"/collections/{name}")
        if resp.status_code == 200:
            await self._ensure_indexes(name)
            return
        create = await self._client.put(f"/collections/{name}", json={
            "vectors": {"size": dim, "distance": "Cosine"}})
        if create.status_code >= 400:
            raise RuntimeError(f"qdrant create collection {create.status_code}")
        await self._ensure_indexes(name)

    async def _ensure_indexes(self, name: str) -> None:
        """Payload indexes (keyword) are mandatory for filtered search.
        Official REST: PUT /collections/{name}/index {field_name, field_schema}."""
        for field in ("student_id", "document_id"):
            try:
                resp = await self._client.put(
                    f"/collections/{name}/index",
                    json={"field_name": field, "field_schema": "keyword"},
                    params={"wait": "true"})
                if resp.status_code >= 400:
                    log.warning("qdrant_index_create_failed", extra={"ctx": {
                        "field": field, "status": resp.status_code}})
            except httpx.HTTPError as exc:  # best effort
                log.warning("qdrant_index_create_failed", extra={"ctx": {
                    "field": field, "err": str(exc)[:120]}})

    async def upsert(self, ids: list[str], vectors: list[list[float]],
                     payloads: list[dict]) -> None:
        dim = len(vectors[0]) if vectors else 384
        await self.ensure_collection(dim)
        points = [{"id": i, "vector": v, "payload": p}
                  for i, v, p in zip(ids, vectors, payloads)]
        resp = await self._client.put(
            f"/collections/{self._collection(dim)}/points", json={"points": points})
        if resp.status_code >= 400:
            raise RuntimeError(f"qdrant upsert {resp.status_code}: {resp.text[:200]}")

    async def search(self, vector: list[float], *, k: int = 5,
                     filter_student: Optional[str] = None,
                     filter_document: Optional[str] = None) -> list[ScoredPoint]:
        """Modern Query API (POST /points/query) — returns payloads."""
        must = []
        if filter_student:
            must.append({"key": "student_id", "match": {"value": filter_student}})
        if filter_document:
            must.append({"key": "document_id", "match": {"value": filter_document}})
        body: dict = {"query": vector, "limit": k, "with_payload": True}
        if must:
            body["filter"] = {"must": must}
        resp = await self._client.post(
            f"/collections/{self._collection(len(vector))}/points/query", json=body)
        if resp.status_code >= 400:
            raise RuntimeError(f"qdrant search {resp.status_code}: {resp.text[:200]}")
        points = resp.json().get("result", {}).get("points", [])
        return [ScoredPoint(score=h.get("score", 0.0), payload=h.get("payload") or {})
                for h in points]

    async def delete_document(self, document_id: str) -> None:
        for dim in (get_settings().gemini_embedding_dim, 384):
            await self._client.post(
                f"/collections/{self._collection(dim)}/points/delete",
                json={"filter": {"must": [{"key": "document_id",
                                           "match": {"value": document_id}}]}})


class MemoryVectorStore:
    """Cosine-similarity fallback (isolated per student/document via filters)."""
    name = "memory"

    def __init__(self) -> None:
        self._points: dict[str, tuple[list[float], dict]] = {}

    async def ensure_collection(self, dim: int) -> None:
        return

    async def upsert(self, ids, vectors, payloads) -> None:
        for i, v, p in zip(ids, vectors, payloads):
            self._points[i] = (v, p)

    async def search(self, vector, *, k=5, filter_student=None,
                     filter_document=None) -> list[ScoredPoint]:
        def ok(payload: dict) -> bool:
            if filter_student and payload.get("student_id") != filter_student:
                return False
            if filter_document and payload.get("document_id") != filter_document:
                return False
            return True

        scored = []
        for v, payload in self._points.values():
            if not ok(payload):
                continue
            num = sum(a * b for a, b in zip(vector, v))
            den = (math.sqrt(sum(x * x for x in vector))
                   * math.sqrt(sum(x * x for x in v))) or 1.0
            scored.append(ScoredPoint(score=num / den, payload=payload))
        scored.sort(key=lambda h: -h.score)
        return scored[:k]

    async def delete_document(self, document_id: str) -> None:
        self._points = {i: (v, p) for i, (v, p) in self._points.items()
                        if p.get("document_id") != document_id}


class VectorService:
    def __init__(self) -> None:
        self._store = None
        self._qdrant_failed = False

    def _ensure(self):
        if self._store is None and not self._qdrant_failed:
            s = get_settings()
            if s.qdrant_url and s.qdrant_api_key:
                try:
                    self._store = QdrantStore()
                except Exception as exc:  # noqa: BLE001
                    log.warning("qdrant_init_failed", extra={"ctx": {"err": str(exc)[:120]}})
                    self._qdrant_failed = True
            else:
                self._qdrant_failed = True
        if self._store is None:
            self._store = MemoryVectorStore()
        return self._store

    @property
    def backend(self) -> str:
        return self._ensure().name

    async def ensure_collection(self, dim: int) -> None:
        await self._ensure().ensure_collection(dim)

    async def upsert(self, ids, vectors, payloads) -> None:
        store = self._ensure()
        try:
            await store.upsert(ids, vectors, payloads)
        except Exception as exc:  # noqa: BLE001 — degrade to memory, log honestly
            log.warning("vector_upsert_fallback_memory", extra={"ctx": {"err": str(exc)[:160]}})
            if not isinstance(store, MemoryVectorStore):
                self._store = MemoryVectorStore()
                await self._store.upsert(ids, vectors, payloads)

    async def search(self, vector, **kw):
        store = self._ensure()
        try:
            return await store.search(vector, **kw)
        except Exception as exc:  # noqa: BLE001
            log.warning("vector_search_fallback_memory", extra={"ctx": {"err": str(exc)[:160]}})
            if not isinstance(store, MemoryVectorStore):
                self._store = MemoryVectorStore()
                return await self._store.search(vector, **kw)
            raise

    async def delete_document(self, document_id: str) -> None:
        try:
            await self._ensure().delete_document(document_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("vector_delete_failed", extra={"ctx": {"err": str(exc)[:120]}})


vector_store = VectorService()