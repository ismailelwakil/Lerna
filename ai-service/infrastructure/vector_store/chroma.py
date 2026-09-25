from __future__ import annotations

from pathlib import Path
from typing import Any

from src.contracts.models import Chunk


class ChromaVectorStore:
    """Persistent Chroma-backed vector store.

    The adapter supplies embeddings explicitly, so Chroma's own embedding
    function is not used for add/query operations. Collection creation is
    compatible with both modern Chroma (configuration=...) and older releases
    that still expect HNSW settings in collection metadata.
    """

    name = "chroma-persistent"

    def __init__(
        self,
        embedder: Any,
        path: str = "data/chroma",
        collection: str = "academic_knowledge",
    ) -> None:
        import chromadb

        self.e = embedder
        self.path = str(path)
        self.collection_name = collection
        Path(self.path).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.path)

        # Chroma 1.x configures the distance metric through `configuration`.
        # Older Chroma versions used collection metadata. Supporting both here
        # avoids forcing the rest of the application to care about SDK details.
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                configuration={"hnsw": {"space": "cosine"}},
            )
        except TypeError:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

    def _embed_document(self, text: str) -> list[float]:
        if hasattr(self.e, "embed_document"):
            return list(self.e.embed_document(text))
        return list(self.e.embed(text))

    def _embed_query(self, text: str) -> list[float]:
        if hasattr(self.e, "embed_query"):
            return list(self.e.embed_query(text))
        return list(self.e.embed(text))

    @staticmethod
    def _metadata_from_chunk(chunk: Chunk) -> dict[str, Any]:
        data = chunk.model_dump(exclude={"text"})
        clean: dict[str, Any] = {}
        for key, value in data.items():
            if value is None:
                clean[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                clean[key] = value
            else:
                clean[key] = str(value)
        return clean

    @staticmethod
    def _chunk_from_result(document: str, metadata: dict[str, Any]) -> Chunk:
        data = dict(metadata)
        data["text"] = document
        for field in ("page", "slide", "owner_id", "section", "source_url", "publisher"):
            if data.get(field) == "":
                data[field] = None
        if "course" not in data or not data["course"]:
            data["course"] = "General"
        return Chunk.model_validate(data)

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        embeddings = [self._embed_document(text) for text in documents]
        metadatas = [self._metadata_from_chunk(chunk) for chunk in chunks]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    @staticmethod
    def _where(owner_id: str | None, document_ids: list[str] | None, course: str | None = None) -> dict[str, Any] | None:
        filters: list[dict[str, Any]] = []
        if owner_id:
            filters.append({"owner_id": {"$eq": owner_id}})
        if document_ids:
            filters.append({"document_id": {"$in": document_ids}})
        if course and course != "General":
            filters.append({"course": {"$eq": course}})
        if len(filters) == 1:
            return filters[0]
        if filters:
            return {"$and": filters}
        return None

    def search(
        self,
        query: str,
        k: int = 8,
        owner_id: str | None = None,
        document_ids: list[str] | None = None,
        course: str | None = None,
    ) -> list[tuple[float, Chunk]]:
        if k <= 0:
            return []

        query_vector = self._embed_query(query)
        result = self.collection.query(
            query_embeddings=[query_vector],
            n_results=k,
            where=self._where(owner_id, document_ids, course),
            include=["documents", "metadatas", "distances"],
        )

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        output: list[tuple[float, Chunk]] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            chunk = self._chunk_from_result(document, metadata or {})
            score = max(0.0, min(1.0, 1.0 - float(distance)))
            output.append((score, chunk))
        return output

    def list_chunks(
        self,
        owner_id: str | None = None,
        document_ids: list[str] | None = None,
        course: str | None = None,
    ) -> list[Chunk]:
        result = self.collection.get(
            where=self._where(owner_id, document_ids, course),
            include=["documents", "metadatas"],
        )

        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        return [
            self._chunk_from_result(document, metadata or {})
            for document, metadata in zip(documents, metadatas)
        ]

    def delete_document(self, document_id: str) -> None:
        self.collection.delete(where={"document_id": {"$eq": document_id}})

    def count(self) -> int:
        return int(self.collection.count())

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "collection": self.collection_name,
            "path": self.path,
            "records": self.count(),
            "persistent": True,
        }
