# INTEGRATION — wiring this module into the main EDUnation platform

## Principles

- This module does **not** own users, sessions, learner profiles, or chat
  memory. It receives an authenticated caller (`X-API-Key`) plus an opaque
  student identity (`X-Student-Id`) and learner context in request bodies.
- All results reference `student_id` / `course_id` strings you already own.

## 1. Authentication expectations

```
X-API-Key:   <CONTENT_API_KEY>          (server-to-server secret)
X-Student-Id: <your user id>            (≤64 chars)
X-Course-Id:  <optional course id>      (or course_id in the body)
```

## 2. Learner context format (in request bodies)

```json
"level": "beginner|intermediate|advanced|expert",
"learner": {
  "major": "CS", "course": "Networking", "learning_goal": "become a pentester",
  "knowledge_gaps": ["subnetting"], "misconceptions": ["DNS is only for websites"],
  "strong_areas": ["linux"], "weak_areas": ["tcp"],
  "learning_preferences": ["visual"], "previous_content_performance": {"quiz_avg": 0.7}
}
```

Personalization is applied automatically: level → vocabulary/depth/analogies;
gaps/misconceptions are explicitly targeted in prompts and exams.

## 3. Typical flows

**Upload → teach from material**
```
POST /api/v1/content/documents/upload           (multipart) → document_id
POST /api/v1/content/documents/{id}/process     → job_id (poll /jobs/{id})
POST /api/v1/content/from-document
     {"document_ids":[id], "instruction":"Create 20 MCQs"}
POST /api/v1/content/from-document
     {"instruction":"Summarize this"} / "Teach me this material" / "Create flashcards"
```

**Adaptive re-explanation** — when the student says "I don't understand":
```
POST /api/v1/content/explain
     {"topic": "...", "re_explain_of": "<previous content_id>"}
```
The engine automatically advances the teaching strategy
(simple → analogy → real-world → visual → step-by-step → practice → prerequisites).

**Exam with answer keys kept server-side** — request with `include_answers:
false` when forwarding to a student client; re-request with `true` from your
backend for grading UIs.

**Voice**: POST `/audio` returns a signed URL (mp3) — your tutor frontend owns
play/pause/stop. For interruption ("Stop — what does SYN mean?"): stop playback
client-side, send the question to your tutor, then re-request audio from the
preserved lesson position (the module is stateless about conversations by
design — see §6).

**Video**: POST `/video` → job; poll `GET /jobs/{id}` through
QUEUED→SCRIPTING→VERIFYING→SCENE_GENERATION→ASSEMBLING→QUALITY_CHECK→COMPLETED;
the result contains per-scene audio (signed URLs), visuals, subtitles and an
interactive player URL.

## 4. Content response contract

```json
{
  "meta": {"content_id": "...", "type": "explanation", "topic": "DNS",
           "difficulty": "medium", "student_level": "beginner",
           "source_ids": ["doc..."], "source_refs": [{"document_id": "...", "page": 2}],
           "verified": true, "verification": {"passed": true, "checker": "rules+model"},
           "grounded": true, "provider": "openrouter", "model": "...",
           "usage": {"input_tokens": 800, "output_tokens": 600},
           "estimated_cost_usd": 0.0031, "created_at": "...", "version": 1},
  "content": {"text": "...", "external_knowledge": false}
}
```

Question sets: `{set_id, kind, topic, difficulty, student_level, document_id,
total, questions: [{question_id, type, question, options, correct_answer?,
explanation?, difficulty, blooms, learning_objective, source_reference?}]}`.

## 5. Errors

`{"error": {"code": "CONTENT_GENERATION_FAILED|INSUFFICIENT_SOURCE|
PROVIDER_UNAVAILABLE|IMAGE_PROVIDER_UNAVAILABLE|TTS_PROVIDER_UNAVAILABLE|
QUOTA_EXCEEDED|RATE_LIMITED|UNAUTHORIZED|NOT_FOUND|UNSUPPORTED_FILE_TYPE|...",
"message": "...", "request_id": "..."}}` — map `INSUFFICIENT_SOURCE` to a
friendly "upload more material" UX.

## 6. Ownership boundaries & future webhooks

- Conversation memory, learner model, progress tracking: **yours**. This module
  stores only generated artifacts + verification + telemetry.
- Suggested integration hooks (not yet exposed): job completion webhooks
  (`POST <your_url>` with the `GET /jobs/{id}` body) and a `content_consumed`
  event for analytics — both are one-line additions in `app/workers/worker.py`.
- Cost dashboards: read `provider_requests` (per provider/model/ student/ day)
  or connect Langfuse.

## 7. Deployment notes

- Run behind your edge with TLS; only expose `/api/v1/*` + `/health`.
- Set `CONTENT_API_KEY` to a fresh random value and share it with the core
  backend via secret manager only.
- Scale: any number of stateless replicas + Postgres + Redis + Qdrant Cloud
  (already used) — or in-memory single node for dev.