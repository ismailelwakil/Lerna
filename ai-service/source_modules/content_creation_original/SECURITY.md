# SECURITY — Content Creation Module

## Controls implemented

**Access & authoritative identity**
- Module-level auth: `X-API-Key` (constant-time compare) on every route; the
  main platform authenticates end users and forwards `X-Student-Id`.
- **The authenticated identity is authoritative.** A `student_id` inside a
  request body is advisory only: if it conflicts with `X-Student-Id` the
  request is rejected with 403, and every ownership operation (persistence,
  storage, jobs, quotas) uses the header identity — body values can never
  create resources as another student. Enforced centrally via
  `student_identity` + `authorize_student` in `app/api/dependencies.py` and
  covered by `tests/test_security_regression.py`.
- Production startup **fails closed** when `CONTENT_API_KEY` is not set
  explicitly (`validate_production_config`); running key-less is possible only
  in dev/test and is documented as open mode for local development.
- Production likewise **requires an explicit `ASSET_SIGNING_SECRET`** (stable
  across instances/restarts) and, when `STORAGE_PROVIDER=supabase`, complete
  Supabase credentials — production NEVER silently falls back to local
  storage (dev may, with a logged warning).
- Workers re-validate ownership: a background job may only process documents
  owned by the student who created the job (client-supplied job params cannot
  reach another student's material).
- `/health` is minimal liveness (no infrastructure detail); the provider
  readiness snapshot lives at `/internal/health` behind the module API key.
- Object-level authorization (IDOR): every document/job/asset/generated item is
  filtered by `student_id`; probing other users' IDs returns uniform 404s
  (no existence oracle).
- Retrieval isolation: Qdrant/memory searches filter by `student_id` AND
  `document_id`; cross-student retrieval is structurally impossible.

**Uploads**
- Extension whitelist + magic-byte verification + size cap (client MIME is
  never trusted) — mismatched content is rejected.
- **Bounded streaming reads** (`read_bounded`, 1 MiB chunks): oversized
  uploads are abandoned on the first chunk that crosses the limit — a client
  can never force unbounded memory allocation; an early `Content-Length`
  guard rejects known-oversize requests before body parsing. Rejected files
  are never written to storage (no orphans); malware-rejected files are
  deleted from storage.
- Filename sanitization (traversal-proof), UUID storage keys outside the web
  root, private storage; access only via short-lived HMAC-signed URLs
  (expiring, forgery-checked with `compare_digest`).
- Production startup **requires `MALWARE_SCANNER=clamav`** (`none` is the
  dev default and fails closed in production via
  `validate_production_config`).
- Malware scanning: `MALWARE_SCANNER=none` (dev default, honestly labeled
  as *no real protection*) or `clamav` (real INSTREAM scanning over TCP, no
  new dependency). With `REQUIRE_MALWARE_SCANNING=true` the pipeline
  **fails safely**: if no scanner is configured or reachable, the document is
  rejected and the job FAILS — never silently treated as clean.

**Prompt injection & RAG**
- Strict instruction hierarchy in every prompt; retrieved document text is
  tag-neutralized (`<system>`, `</source_context>` stripped) and wrapped as
  UNTRUSTED DATA; injection phrases are filtered; system prompts are never
  returned.

**Abuse & cost**
- Per-student and per-route rate limits; per-student daily quotas
  (request count + estimated USD cost) enforced before expensive generation;
  video jobs per day capped; `MAX_QUESTIONS`, `MAX_UPLOAD_MB`, `MAX_AUDIO_CHARS`
  limits; unauthenticated callers can reach nothing.

**Secrets & errors**
- Keys only in `.env` (gitignored); never in code, responses, or client
  payloads. Logs redact key-like fields and hash nothing sensitive into output.
- All errors use the controlled envelope `{code, message, request_id}` —
  stack traces and provider bodies are logged server-side only.

## Red-team review performed (see tests/test_integration_security.py)

| Attack | Result |
|---|---|
| Missing/forged API key | 401 |
| Body `student_id` spoofing on all 16 generation/job endpoints | 403, no resource created for victim |
| IDOR on /verify (other student's content_id) | 404, nothing leaked |
| IDOR on documents (read/delete/process) | 404, no leak |
| IDOR on jobs | 404 |
| Generation referencing another student's document | 404 |
| Path traversal in filenames (`../../etc/passwd.txt`) | sanitized to `passwd.txt` |
| `.exe` upload / PDF with fake magic bytes | 422 rejected |
| Prompt injection inside uploaded document | neutralized at wrap time |
| Forged/expired/altered/tampered asset signature or traversal key | 403/404 |
| Rate-limit hammering | 429 |
| Oversized payloads | 422/413 |
| Secret leakage in error bodies | none (enforced by tests) |

## Assumptions & residual risks (not claimed "100% secure")

1. The calling platform is trusted to authenticate students and pass the true
   `X-Student-Id` — a compromised core backend can impersonate students.
2. Local storage is private-by-obscurity on the server FS; use the Supabase/S3
   adapter + TLS for hardened deployments.
3. Malware scanning is opt-in: with the dev default
   (`MALWARE_SCANNER=none`, `REQUIRE_MALWARE_SCANNING=false`) no real scanning
   occurs. Production should set `MALWARE_SCANNER=clamav` +
   `REQUIRE_MALWARE_SCANNING=true` and run clamd; the adapter is implemented,
   but its detection quality depends on your ClamAV signature updates.
4. Rate limiting is per-process memory — multi-node deployments need the
   Redis-backed limiter.
5. Generated content is model-verified where sources exist, but LLM factuality
   cannot be guaranteed — the verification verdict ships in every response.
6. Veo/video and image outputs are generation-based; exact technical diagrams
   intentionally use the deterministic SVG path only.