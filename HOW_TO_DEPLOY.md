# How to deploy LeRna on Railway (and get a URL for the backend developer)

You will deploy the **API** (FastAPI + AI). That public HTTPS URL is what you send to the backend developer.

Estimated time: 15–20 minutes (first Docker build is slow because of PyTorch + embeddings).

---

## A. Push the code to GitHub (do not drag-and-drop the folder)

GitHub’s **website upload** rejects files over **25 MB**. The local Chroma DB (`chroma.sqlite3`, ~44 MB) is **still on your disk** but is gitignored so GitHub and Railway accept the repo. It is rebuilt at runtime.

**Use git (not “upload folder”):**

```bash
cd LeRna
git init
git add .
git status   # confirm no chroma.sqlite3 and no .env
git commit -m "LeRna API ready for Railway"
git branch -M main
git remote add origin https://github.com/Malak-0sama/LeRna.git
git push -u origin main
```

If the repo already exists and has an old commit:

```bash
git add .
git commit -m "Fix GitHub size limits; keep Railway deploy files"
git push origin main
```

If GitHub still refuses because history already contains the big file:

```bash
git rm -r --cached ai-service/data/chroma ai-service/data/chromadb 2>/dev/null || true
git add .gitignore
git commit -m "Stop tracking large Chroma database files"
git push origin main
```

---

## B. Create the Railway project (API)

1. Open [https://railway.app](https://railway.app) and log in with GitHub.
2. **New Project** → **Deploy from GitHub repo**.
3. Select **Malak-0sama/LeRna**.
4. Railway reads `railway.json` and builds with the root **Dockerfile**.
5. Wait until the first build finishes (often 8–15 minutes).

If Railway asks for a root directory, leave it empty (repo root).

---

## C. Add environment variables

Railway → your **service** → **Variables** → add these.

**Required**

| Name | Value |
| :--- | :--- |
| `GEMINI_API_KEY` | your Gemini API key |
| `TAVILY_API_KEY` | your Tavily API key |
| `AI_PROVIDER` | `gemini` |
| `AI_MODEL` | `gemini-2.0-flash` |
| `ENABLE_WEB_SEARCH` | `true` |
| `CORS_ORIGINS` | `*` |
| `DATA_DIR` | `ai-service/data` |
| `ACADEMIC_OS_DATA_DIR` | `ai-service/data` |
| `CHROMA_PATH` | `ai-service/data/chroma` |
| `ARTIFACTS_DIR` | `ai-service/data/artifacts` |
| `ACADEMIC_OS_TEST_MODE` | `false` |
| `DEFAULT_STUDENT_ID` | `student-001` |
| `EMBEDDING_BACKEND` | `sentence-transformers` |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-small` |
| `VECTOR_BACKEND` | `chroma` |
| `ALLOW_MOCK_FALLBACK` | `false` |

**Do not set `PORT`.** Railway sets it automatically.

After saving variables, Railway will redeploy.

Optional: **Volumes** → mount `/app/ai-service/data` so uploads and Chroma survive restarts.

Use a plan with **at least 2 GB RAM**.

---

## D. Create the public URL

1. Railway → service → **Settings**.
2. **Networking** → **Public Networking** → **Generate Domain**.
3. Copy the domain, for example:

```
https://lerna-production-xxxx.up.railway.app
```

---

## E. Check it works

In a browser or terminal:

```
https://YOUR-DOMAIN.up.railway.app/
https://YOUR-DOMAIN.up.railway.app/docs
https://YOUR-DOMAIN.up.railway.app/openapi.json
https://YOUR-DOMAIN.up.railway.app/health
```

- `/` should return JSON `"status": "online"`.
- `/docs` is Swagger (the backend developer can try endpoints here).
- First `/health` can take up to ~90 seconds while models load.

---

## F. Message to copy to the backend developer

Replace the domain with yours:

```
LeRna / Academic OS API is live.

Base URL:  https://YOUR-DOMAIN.up.railway.app
Swagger:   https://YOUR-DOMAIN.up.railway.app/docs
OpenAPI:   https://YOUR-DOMAIN.up.railway.app/openapi.json
Health:    https://YOUR-DOMAIN.up.railway.app/health

Auth for this handoff:
  Header: X-Student-Id: student-001
  or Authorization: Bearer student-001

Main routes:
  GET  /health
  GET  /capabilities
  GET  /students/{id}/profile
  PATCH /students/{id}/preferences
  GET  /students/{id}/learning
  POST /tutor/chat
  GET  /materials
  POST /materials/upload
  POST /study-tools/generate
  POST /assessments/generate
  POST /assessments/{id}/submit
  POST /spaced-repetition/review
  GET  /artifacts/{id}/download

Set client timeouts to 90s for tutor / study tools.
Contract files in repo: docs/API_CONTRACT.md, docs/BACKEND_HANDOFF.md, openapi.json
```

---

## G. (Optional) Deploy the React frontend too

1. Railway → **New service** → same GitHub repo.
2. Set **Root Directory** to `frontend` **or** keep repo root and use `frontend/Dockerfile`.
3. Variables / Docker build args:
   - `VITE_API_BASE_URL` = `https://YOUR-API-DOMAIN.up.railway.app`
   - `VITE_DEMO_STUDENT_ID` = `student-001`
4. Generate a second public domain for the UI.

If you only need a URL for the **backend developer**, skip this — they only need the API.

---

## Files this repo uses for deploy

| File | Role |
| :--- | :--- |
| `Dockerfile` | Production image for the API |
| `railway.json` | Tells Railway to use Docker + healthcheck |
| `Procfile` | Start command fallback |
| `requirements.txt` | Python packages |
| `start.sh` | uvicorn start script |
| `.env.example` | Variable template (copy into Railway) |
| `api/main.py` | FastAPI app (`PORT`, CORS) |
| `frontend/Dockerfile` | Optional UI image |
| `frontend/nginx.conf` | SPA routing for the UI |
| `HOW_TO_DEPLOY.md` | This guide |

---

## Common problems

| Problem | Fix |
| :--- | :--- |
| Build fails on Torch | Dockerfile already installs CPU Torch first. Retry the deploy. |
| Healthcheck fails | Must hit `/` not `/health`. `railway.json` already uses `/`. |
| 502 / out of memory | Upgrade RAM to 2GB+. |
| CORS errors from a website | Set `CORS_ORIGINS` to that site origin, or `*` for testing. |
| Empty replies / mock AI | `GEMINI_API_KEY` missing or `ACADEMIC_OS_TEST_MODE=true`. |
| Files lost after restart | Add a Railway volume on `/app/ai-service/data`. |
