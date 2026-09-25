from __future__ import annotations

import sys
import types
from pathlib import Path

from infrastructure.vector_store.chroma import ChromaVectorStore
from src.contracts.models import Chunk


class FakeEmbedder:
    def embed(self, text: str):
        return [1.0, 0.0]


class FakeCollection:
    def __init__(self):
        self.rows = {}

    def upsert(self, ids, documents, embeddings, metadatas):
        for i, document, embedding, metadata in zip(ids, documents, embeddings, metadatas):
            self.rows[i] = (document, embedding, metadata)

    def query(self, **kwargs):
        if not self.rows:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        document, _, metadata = next(iter(self.rows.values()))
        return {"documents": [[document]], "metadatas": [[metadata]], "distances": [[0.1]]}

    def get(self, **kwargs):
        rows = list(self.rows.values())
        return {
            "documents": [row[0] for row in rows],
            "metadatas": [row[2] for row in rows],
        }

    def delete(self, where):
        document_id = where["document_id"]["$eq"]
        self.rows = {
            key: value for key, value in self.rows.items()
            if value[2].get("document_id") != document_id
        }

    def count(self):
        return len(self.rows)


class FakeClient:
    def __init__(self, path, calls):
        self.path = path
        self.calls = calls
        self.collection = FakeCollection()

    def get_or_create_collection(self, **kwargs):
        self.calls.append(kwargs)
        return self.collection


def test_chroma_uses_current_name_keyword_and_roundtrips_chunk(monkeypatch, tmp_path: Path):
    calls = []

    fake_module = types.SimpleNamespace(
        PersistentClient=lambda path: FakeClient(path, calls)
    )
    monkeypatch.setitem(sys.modules, "chromadb", fake_module)

    store = ChromaVectorStore(FakeEmbedder(), str(tmp_path / "chroma"))
    assert calls[0]["name"] == "academic_knowledge"
    assert calls[0]["configuration"]["hnsw"]["space"] == "cosine"

    chunk = Chunk(
        chunk_id="c1",
        document_id="d1",
        text="CNN filters learn local visual patterns.",
        source="course.pdf",
        page=1,
        authority="student_upload",
        trust_score=1.0,
        owner_id="student-1",
        language="en",
    )
    store.add([chunk])

    matches = store.search("CNN filters", k=1, owner_id="student-1")
    assert len(matches) == 1
    score, restored = matches[0]
    assert score == 0.9
    assert restored.chunk_id == "c1"
    assert restored.page == 1
    assert store.health()["records"] == 1