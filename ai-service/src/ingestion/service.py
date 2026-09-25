from __future__ import annotations
import shutil, uuid, re, json, hashlib, os
from pathlib import Path
from infrastructure.document_loaders.loaders import safe_name, extract
from src.contracts.models import DocumentMeta, Chunk
from src.core.exceptions import DocumentError

class IngestionService:
    def __init__(self, vector_store, upload_dir='data/uploads', chunk_size=1200, overlap=180, max_upload_mb=25):
        self.v = vector_store
        self.dir = Path(upload_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_bytes = max_upload_mb * 1024 * 1024
        self.manifest = self.dir / 'manifest.json'

    def _manifest(self):
        if not self.manifest.exists():
            return {}
        try:
            return json.loads(self.manifest.read_text(encoding='utf-8'))
        except Exception as exc:
            raise DocumentError('Upload manifest is corrupted') from exc

    def _write_manifest(self, m):
        tmp = self.manifest.with_suffix('.tmp')
        tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, self.manifest)

    def _chunks(self, text):
        paras = [x.strip() for x in re.split(r'\n\s*\n|(?<=[.!?])\s+(?=[A-Z\u0600-\u06ff\u1200-\u137f])', text) if x.strip()]
        out = []
        cur = ''
        for p in paras:
            if len(cur) + len(p) + 1 <= self.chunk_size:
                cur = (cur + ' ' + p).strip()
            else:
                if cur:
                    out.append(cur)
                tail = cur[-self.overlap:] if cur else ''
                cur = (tail + ' ' + p).strip()
                while len(cur) > self.chunk_size * 1.5:
                    out.append(cur[:self.chunk_size])
                    cur = cur[self.chunk_size - self.overlap:]
        if cur:
            out.append(cur)
        return [x for x in out if x.strip()]

    def list_documents(self, owner_id, source_type='student_upload', course=None):
        items = []
        for raw in self._manifest().values():
            try:
                meta = DocumentMeta.model_validate(raw)
            except Exception:
                continue
            if meta.owner_id == owner_id and (source_type is None or meta.source_type == source_type):
                if course is None or getattr(meta, 'course', 'General') == course or course == 'General':
                    items.append(meta)
        return sorted(items, key=lambda x: x.created_at, reverse=True)

    def ingest(self, src, filename, owner_id, course='General'):
        filename = safe_name(filename)
        src = Path(src)
        if not src.exists() or not src.is_file():
            raise DocumentError('Uploaded file does not exist')
        if src.stat().st_size > self.max_bytes:
            raise DocumentError(f'File exceeds {self.max_bytes // (1024 * 1024)} MB upload limit')
        raw = src.read_bytes()
        if not raw:
            raise DocumentError('Uploaded file is empty')
        digest = hashlib.sha256(raw).hexdigest()
        m = self._manifest()
        key = f'upload:{owner_id}:{course}:{digest}'
        if key in m:
            return DocumentMeta.model_validate(m[key])
        did = str(uuid.uuid4())
        dst = self.dir / f'{did}_{filename}'
        shutil.copyfile(src, dst)
        pages = extract(dst)
        chunks = []
        for page, text in pages:
            clean = re.sub(r'[ \t]+', ' ', text).strip()
            for i, piece in enumerate(self._chunks(clean)):
                chunks.append(Chunk(
                    chunk_id=f'{did}:{page}:{i}',
                    document_id=did,
                    text=piece,
                    source=filename,
                    page=page,
                    authority='student_upload',
                    trust_score=1.0,
                    owner_id=owner_id,
                    source_type='student_upload',
                    course=course or 'General',
                ))
        if not chunks:
            dst.unlink(missing_ok=True)
            raise DocumentError('No readable text could be extracted from the document')
        self.v.add(chunks)
        meta = DocumentMeta(
            document_id=did,
            filename=filename,
            owner_id=owner_id,
            pages=len(pages),
            chunks=len(chunks),
            indexed=True,
            source_type='student_upload',
            course=course or 'General',
        )
        m[key] = meta.model_dump()
        self._write_manifest(m)
        return meta

    def ingest_external(self, sources, owner_id, course='General'):
        m = self._manifest()
        metas = []
        for source in sources:
            url = str(source.get('url', '')).strip()
            text = re.sub(r'\s+', ' ', str(source.get('text', ''))).strip()
            if not url or len(text) < 30:
                continue
            digest = hashlib.sha256((url + '\n' + text).encode('utf-8')).hexdigest()
            key = f'external:{owner_id}:{digest}'
            if key in m:
                metas.append(DocumentMeta.model_validate(m[key]))
                continue
            did = 'web-' + hashlib.sha256((owner_id + '|' + url).encode()).hexdigest()[:24]
            pieces = self._chunks(text)
            chunks = []
            for i, piece in enumerate(pieces):
                chunks.append(Chunk(
                    chunk_id=f'{did}:1:{i}',
                    document_id=did,
                    text=piece,
                    source=source.get('title') or url,
                    page=1,
                    authority=source.get('authority', 'unverified'),
                    trust_score=float(source.get('trust_score', 0.25)),
                    owner_id=owner_id,
                    source_type='trusted_external',
                    source_url=url,
                    publisher=source.get('publisher') or source.get('domain'),
                    course=course or 'General',
                ))
            if not chunks:
                continue
            self.v.add(chunks)
            meta = DocumentMeta(
                document_id=did,
                filename=source.get('title') or source.get('domain') or 'Trusted source',
                owner_id=owner_id,
                pages=1,
                chunks=len(chunks),
                indexed=True,
                source_type='trusted_external',
                source_url=url,
                publisher=source.get('publisher') or source.get('domain'),
                trust_score=float(source.get('trust_score', 0.25)),
                course=course or 'General',
            )
            m[key] = meta.model_dump()
            metas.append(meta)
        if metas:
            self._write_manifest(m)
        return metas
