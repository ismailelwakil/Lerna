# Backend Developer Integration Guide: Academic OS

This guide explains how a Backend Engineer should integrate, host, authenticate, and scale the Academic OS AI intelligence engine.

---

## 1. Subsystem Interaction Architecture

Academic OS provides a single, high-level facade entry point: `LearningIntelligenceModule` (instantiated via `build_module(data_dir=None, test_mode=False)`).

```python
from src.integration.service import build_module

# Production initialization
ai = build_module(data_dir="./data", test_mode=False)

# Or test mode with zero external network dependency
ai_test = build_module(test_mode=True)
```

The thin API facade (`api/main.py`) exposes this engine over standard HTTP/REST endpoints. The Backend Developer can either:
1. **Deploy the included FastAPI facade directly** (`uvicorn api.main:app`).
2. **Mount the routers into an existing FastAPI/Django/Flask backend** (`app.include_router(tutor_router)`).
3. **Invoke `LearningIntelligenceModule` directly in-process** from existing microservices.

---

## 2. Authentication & Identity Integration

In the demo package, identity defaults to `student-001` or the value in `VITE_DEMO_STUDENT_ID`.
To connect your production user accounts (OAuth, JWT, Session cookies):

1. Edit `api/dependencies.py`:
   ```python
   def get_current_student_id(
       authorization: Optional[str] = Header(None),
   ) -> str:
       if not authorization or not authorization.startswith("Bearer "):
           raise HTTPException(status_code=401, detail="Authentication required")
       
       token = authorization.split(" ")[1]
       # Verify JWT signature:
       payload = decode_jwt(token)
       student_id = payload["sub"]  # or user.id
       return student_id
   ```
2. The AI Tutor and profile loaders will automatically use the resolved `student_id` for per-user concept mastery, uploaded materials, and study plans.

---

## 3. Course Materials Ingestion & Routing Modes

Academic OS supports two strictly isolated retrieval modes:

### Mode A: Selected Course Materials (`document_ids = [...]`)
- When the student selects specific uploaded materials:
  ```python
  response = ai.ask_tutor(
      student_id=student_id,
      course_id=course,
      text=query,
      document_ids=["doc_uuid_1", "doc_uuid_2"],
  )
  ```
- **Guaranteed Isolation:** The engine runs hybrid BM25 + dense vector search **only** against the chunks of those documents. Zero external Tavily or Google searches are performed.
- If the uploaded document does not contain enough evidence, the engine safely refuses with:
  *"The selected course material does not contain enough information about '{topic}' to answer without model-memory speculation."*

### Mode B: Trusted External Discovery (`document_ids = None` or `[]`)
- When no specific document is selected:
  ```python
  response = ai.ask_tutor(
      student_id=student_id,
      course_id=course,
      text=query,
      document_ids=None,
  )
  ```
- **Trust Filtering:** The engine formulates academic search queries (targeting Tier-A university lecture notes and textbooks) and executes them via Tavily.
- **Strict Invariant:** Domains with trust score $< 0.80$ (commercial SEO blogs, forums, video platforms) are filtered out.
- **Provenance:** Every used chunk attaches exact page numbers, source URLs, and excerpts.

---

## 4. Diagnostic Assessment Lifecycle

```
1. Client requests assessment:
   POST /assessments/generate { "student_id": "...", "topic": "Binary Search" }
   -> Backend creates DiagnosticAssessment and caches it by assessment_id.
   -> Returns questions with MCQs, short answers, and "I don't know" options.

2. Student completes answers in React UI.

3. Client submits answers:
   POST /assessments/{assessment_id}/submit { "answers": { ... } }
   -> Backend calls ai.submit_diagnostic(...)
   -> Server computes score, checks rubric, updates student mastery in JSON profile,
      refreshes spaced repetition intervals (SM-2), and generates Next Best Action.
   -> Returns updated scores and per-question feedback.
```

**Rule:** The frontend must never calculate correctness or update mastery client-side. The backend is the single source of truth.

---

## 5. Artifact Storage & MIME Handling

Generated artifacts (e.g. SVG diagrams and PowerPoint slide decks) are stored locally in:
`data/artifacts/{filename}`

- **Diagrams (`.svg`):** Served with `Content-Type: image/svg+xml`. React previews inline or triggers download.
- **Presentations (`.pptx`):** Served with `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation` and `Content-Disposition: attachment; filename="{filename}"`.
- In production with multi-instance deployments, mount `data/artifacts/` to an S3/GCS bucket or shared persistent volume.

---

## 6. Environment Variables

Configure in `.env`:

```env
# AI & LLM Providers
GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Embeddings & Vector DB
EMBEDDING_MODEL=intfloat/multilingual-e5-small
TRUST_THRESHOLD=0.80
DATA_DIR=/path/to/persistent/data

# Server Configuration
PORT=8000
ACADEMIC_OS_TEST_MODE=false
DEFAULT_STUDENT_ID=student-001
```

---

## 7. Production Deployment Recommendations

1. **Gunicorn / Uvicorn Workers:**
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.main:app --bind 0.0.0.0:8000
   ```
2. **Persistent Storage:** Ensure `data/profiles/`, `data/uploads/`, `data/artifacts/`, and `data/chroma/` are mounted on persistent disk.
3. **CORS Configuration:** Update `allow_origins` in `api/main.py` with your production frontend domain.
4. **Timeouts:** External search and multi-chunk PDF retrieval typically complete in 4–12 seconds. Set reverse proxy (Nginx/Cloudflare) timeouts to $\ge 60$ seconds.
