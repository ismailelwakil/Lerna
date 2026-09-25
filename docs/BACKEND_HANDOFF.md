# Backend developer handoff — Academic OS API

Replace `BASE_URL` with the Railway public URL after deploy (example: `https://lerna-production.up.railway.app`).

## Base URL

```
BASE_URL = https://<railway-public-domain>
```

| Resource | Path |
| :--- | :--- |
| Liveness | `GET /` or `GET /livez` |
| Subsystem health | `GET /health` |
| Capabilities | `GET /capabilities` |
| Swagger | `GET /docs` |
| OpenAPI 3 | `GET /openapi.json` |

## Auth (current handoff)

Production JWT is **not** wired yet. Identity:

1. `X-Student-Id: student-001` (preferred for integration)
2. `Authorization: Bearer <student_id>`
3. Default: `student-001`

Swap `get_current_student_id` in `api/dependencies.py` for JWT when ready.

## Endpoints

| Method | Path | Notes |
| :--- | :--- | :--- |
| GET | `/students/{id}/profile` | Profile + mastery |
| PATCH | `/students/{id}/preferences` | Learning prefs |
| GET | `/students/{id}/learning` | Next best action, plan, reviews |
| POST | `/tutor/chat` | Evidence-grounded tutor. Body includes `text`, `course_id`, `document_ids` (`null` = trusted web) |
| GET | `/materials` | Uploaded docs |
| POST | `/materials/upload` | multipart file |
| POST | `/study-tools/generate` | flashcards, SVG, PPTX |
| POST | `/assessments/generate` | Diagnostic quiz |
| POST | `/assessments/{id}/submit` | Server-side grading |
| POST | `/spaced-repetition/review` | SM-2 feedback |
| GET | `/artifacts/{id}/download` | `.pptx` / `.svg` |

See `docs/API_CONTRACT.md` and `docs/openapi.json` for schemas.

## Integration options

1. **Call this Railway service over HTTP** from your Node/Django/Go backend (recommended).
2. **Mount** `api/routes/*` into an existing FastAPI app.
3. **In-process** `from src.integration.service import build_module`.

## CORS

`CORS_ORIGINS` on Railway. Use `*` during integration, then lock to your frontend origin.

## Timeouts

Tutor / RAG / Tavily: 4–60s. Client timeout ≥ 90s.

## Do not

- Grade assessments or compute mastery on the client.
- Ship API keys to the frontend.
- Call `/health` as a high-frequency probe — use `/` or `/livez`.
