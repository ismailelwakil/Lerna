# Railway deployment — Academic OS API

This service is the **FastAPI integration facade + Python AI engine**. After deploy, send the public URL to the backend developer.

## 1. Push this repo to GitHub

Railway builds from GitHub. Commit the Railway files (`Dockerfile`, `railway.json`, `requirements.txt`, updated `api/main.py`) and push to `main`.

## 2. Create the Railway project

1. Go to [https://railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → `Malak-0sama/LeRna`.
2. Railway will detect `railway.json` and build with the **Dockerfile**.
3. First build downloads PyTorch + `intfloat/multilingual-e5-small`. Expect **8–15 minutes**.

## 3. Set environment variables

In Railway → service → **Variables**, paste from `.env.example`. **Required for real AI:**

| Variable | Example |
| :--- | :--- |
| `GEMINI_API_KEY` | your Gemini key |
| `TAVILY_API_KEY` | your Tavily key |
| `AI_PROVIDER` | `gemini` |
| `ENABLE_WEB_SEARCH` | `true` |
| `CORS_ORIGINS` | `*` (or your frontend origin) |
| `ACADEMIC_OS_TEST_MODE` | `false` |
| `DATA_DIR` | `ai-service/data` |
| `ACADEMIC_OS_DATA_DIR` | `ai-service/data` |
| `CHROMA_PATH` | `ai-service/data/chroma` |

Do **not** set `PORT` — Railway provides it.

Optional volume (persist uploads / chroma / profiles):

- Mount path: `/app/ai-service/data`

## 4. Generate a public URL

Railway → service → **Settings** → **Networking** → **Generate Domain**.

You will get something like:

```
https://lerna-production-xxxx.up.railway.app
```

That is the URL to send to the backend developer.

## 5. Verify

```bash
curl https://YOUR-APP.up.railway.app/
curl https://YOUR-APP.up.railway.app/health
curl https://YOUR-APP.up.railway.app/openapi.json
```

- `/` and `/livez` — liveness (used by Railway healthcheck)
- `/docs` — Swagger UI
- `/openapi.json` — contract for backend/frontend
- `/health` — initializes AI (first call can take 30–90s)

## 6. What to send the backend developer

```
Base URL:  https://YOUR-APP.up.railway.app
Docs:      https://YOUR-APP.up.railway.app/docs
OpenAPI:   https://YOUR-APP.up.railway.app/openapi.json
Health:    https://YOUR-APP.up.railway.app/health

Auth (handoff):
  Header X-Student-Id: student-001
  or Authorization: Bearer <student_id>

Identity is resolved in api/dependencies.py — replace with JWT later.
```

Full contract: `docs/API_CONTRACT.md` and `docs/BACKEND_INTEGRATION_GUIDE.md`.

## 7. Frontend

Set:

```
VITE_API_BASE_URL=https://YOUR-APP.up.railway.app
```

If the frontend is hosted elsewhere, add that origin to `CORS_ORIGINS`.

## Resource notes

Sentence-transformers + Chroma needs **≥ 2 GB RAM**. Use Railway **Hobby** or higher. Tutor / study-tool calls may take 10–60s — keep proxy timeouts ≥ 75s (already set in uvicorn).
