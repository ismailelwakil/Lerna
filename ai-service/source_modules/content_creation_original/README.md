# EDUnation — Content Creation Module

A self-contained, production-quality **generative content engine** for the EDUnation
platform: explanations, study guides, flashcards, grounded document-based exams,
deterministic diagrams, generative images, TTS audio, and scene-based educational
videos — behind replaceable provider abstractions, with verification, RAG, cost
control and observability.

**Scope:** ONLY the Content Creation subsystem + its integration contracts.
It does not re-implement EDUnation's auth, learner model, or tutor orchestration
(see `INTEGRATION.md`).

---

## Architecture

```
API (versioned /api/v1)          ← thin handlers, provider calls forbidden
 ↓ dependencies (X-API-Key + X-Student-Id + rate/quota guards)
Services / Orchestrator          ← ContentOrchestrator decides type, sources,
 ↓                                 provider, verification, persistence
Providers (abstractions)         ← LLM · Embedding · Image · Video · TTS · STT
 ↓                                 VectorStore · Storage · Observability
Provider implementations         ← OpenRouter (+Groq/OpenAI fallback) · Gemini
                                   ElevenLabs · Deepgram · Qdrant · Local/Supabase
                                   storage · Langfuse
Workers                          ← async jobs (document pipeline, audio, video, exams)
```

Generation flow (example — "Create a quiz from this lecture"):
auth → validate → document ownership → extraction → chunks+embeddings →
retrieval → question blueprint → structured generation → per-question
validation (regenerate ONLY failures) → persistence with source references.

## Setup

```bash
cd content_creation
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # fill your keys (all optional — graceful degradation)

uvicorn app.main:app --port 8001     # interactive docs: http://localhost:8001/api/v1/docs
```

Docker: `docker compose up -d` (web + optional local Qdrant).

## Environment variables

See `.env.example` for the complete list. Provider roles:

| Purpose | Provider | Variables | Unconfigured behavior |
|---|---|---|---|
| Text/reasoning LLM | OpenRouter | `OPENROUTER_API_KEY` + 4 role models | `CONTENT_LLM_MODE=mock` offline pipeline |
| Fast/direct fallback | Groq / OpenAI | `GROQ_API_KEY` / `OPENAI_API_KEY` | chain shortens |
| Embeddings | Gemini | `GEMINI_API_KEY` | local hashed embeddings (384-dim) |
| Images / Video (Veo) | Gemini | `GEMINI_API_KEY` + model names | `*_PROVIDER_UNAVAILABLE` |
| Text-to-speech | ElevenLabs → OpenAI | `ELEVENLABS_API_KEY` | `TTS_PROVIDER_UNAVAILABLE` |
| Speech-to-text | Deepgram → OpenAI | `DEEPGRAM_API_KEY` | `STT_PROVIDER_UNAVAILABLE` |
| Vector DB | Qdrant | `QDRANT_URL` + `QDRANT_API_KEY` | in-memory store |
| Object storage | local / Supabase | `STORAGE_PROVIDER` (+SUPABASE_*) | private local + signed URLs |
| Observability | Langfuse | `LANGFUSE_*` | no-op |

Model IDs are **validated against OpenRouter's live catalog** at runtime; a
configured-but-missing model falls back with a logged warning (never fabricated).

## API (v1)

```
POST /api/v1/content/explain | summarize | notes | study-guide | examples | flashcards
POST /api/v1/content/quiz | exam | practice | question-bank (+ /question-bank/filter)
POST /api/v1/content/documents/upload           multipart; PDF/DOCX/PPTX/TXT/images/audio
POST /api/v1/content/documents/{id}/process     async job: extract→chunk→embed→index
POST /api/v1/content/from-document              natural language ("Create 20 MCQs.")
POST /api/v1/content/diagram                    deterministic SVG (flow/sequence)
POST /api/v1/content/image                      Gemini illustration (non-exact visuals)
POST /api/v1/content/audio                      TTS (auto job for long text)
POST /api/v1/content/video                      full async scene pipeline (job)
POST /api/v1/content/verify                     re-verify a content item
POST /api/v1/content/jobs ; GET /jobs/{id} ; GET /jobs/{id}/status
GET  /api/v1/content/assets/{key}?exp=&sig=     HMAC-signed private asset URLs
GET  /health                                    provider readiness snapshot
```

Every response/meta carries: `content_id, type, topic, difficulty, student_level,
source_ids, source_refs, created_at, version, verified, verification, grounded,
provider, model, usage, estimated_cost_usd`.

Errors are always `{"error": {"code", "message", "request_id"}}` — never a stack trace.

**Authorization model:** `X-Student-Id` is the authoritative identity. A body
`student_id` that conflicts with the header returns 403; all objects (content,
documents, jobs, assets) are looked up with id AND owner in a single query.
Production refuses to start without an explicit `CONTENT_API_KEY`.

## Database & workers

- SQLAlchemy models (`app/db/models.py`): uploaded_documents, document_chunks,
  content_items, question_sets, questions, generation_jobs, generated_assets,
  provider_requests, content_verifications. Learner/course identities are
  opaque references (`student_id`, `course_id`) owned by the main platform.
- Dev: SQLite auto-created. Production: set `DATABASE_URL` (Postgres) and use
  Alembic (see `migrations/README.md`).
- Jobs: DB-persisted, in-process asyncio workers (4 concurrent). Long tasks —
  document processing, large exams, long audio, video — never block HTTP.
  Swap in Celery/RQ later by reusing the same handler functions.

## Testing

```bash
python -m pytest tests -q        # 42 tests; fully offline (mocked providers)
```

Covers schemas, upload validation (extension+magic bytes+size), path traversal,
prompt injection neutralization, signed URLs, IDOR (documents, jobs, generation),
rate limits, chunking, question validation, blueprint, diagram rendering,
personalization ladder, and the full document→extraction→RAG→generation flow.

## Security

See `SECURITY.md` (controls + red-team review + known limitations).

## Known limitations

1. Video assembly outputs an interactive HTML5 lesson player (per-scene audio +
   visuals + subtitles) rather than an encoded MP4 — no ffmpeg dependency;
   Veo clips can be attached per scene when enabled.
2. Supabase Storage adapter requires `SUPABASE_SERVICE_KEY` (falls back to
   private local storage until provided).
3. In-process job queue is single-node; use Redis/Celery for multi-node.
4. Malware scanning is a hook (`NullScanner`) — integrate ClamAV in production.
5. Answer-key authorization trusts the calling backend (`include_answers` flag).