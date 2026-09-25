import json
from pathlib import Path
from src.contracts.models import Chunk

class LocalVectorStore:
    name = 'local-json-vector-store'

    def __init__(self, embedder, path='data/vector_db/index.json'):
        self.e = embedder
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rows = []
        if self.path.exists():
            try:
                self.rows = json.loads(self.path.read_text(encoding='utf-8'))
            except Exception:
                self.rows = []

    def add(self, chunks):
        ids = {r['chunk']['chunk_id'] for r in self.rows}
        for c in chunks:
            if c.chunk_id not in ids:
                v = self.e.embed_document(c.text) if hasattr(self.e, 'embed_document') else self.e.embed(c.text)
                self.rows.append({'chunk': c.model_dump(), 'v': v})
        self.path.write_text(json.dumps(self.rows, ensure_ascii=False), encoding='utf-8')

    def list_chunks(self, owner_id=None, document_ids=None, course=None):
        out = []
        for r in self.rows:
            try:
                c = Chunk.model_validate(r['chunk'])
            except Exception:
                continue
            if owner_id is not None and c.owner_id != owner_id:
                continue
            if document_ids is not None and c.document_id not in document_ids:
                continue
            if course is not None and getattr(c, 'course', 'General') != course and course != 'General':
                continue
            out.append(c)
        return out

    def search(self, q, k=5, owner_id=None, document_ids=None, course=None):
        qv = self.e.embed(q)
        out = []
        for r in self.rows:
            try:
                c = Chunk.model_validate(r['chunk'])
            except Exception:
                continue
            if owner_id is not None and c.owner_id != owner_id:
                continue
            if document_ids is not None and c.document_id not in document_ids:
                continue
            if course is not None and getattr(c, 'course', 'General') != course and course != 'General':
                continue
            v = r['v']
            score = sum(a * b for a, b in zip(qv, v))
            out.append((score, c))
        return sorted(out, key=lambda x: x[0], reverse=True)[:k]
