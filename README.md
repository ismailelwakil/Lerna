# Academic OS — Developer Handoff Package

Academic OS is an AI-powered personalized academic learning and intelligence platform designed to replace ungrounded LLM guessing with verified, citation-backed knowledge.

This repository provides a complete, developer-ready handoff package comprising:
1. **`ai-service/`**: The complete Academic OS Python AI/RAG/personalization intelligence engine.
2. **`api/`**: A thin FastAPI backend integration facade exposing standard REST endpoints and OpenAPI contracts.
3. **`frontend/`**: A modern React 19 + TypeScript + Vite single-page application built for student learning.
4. **`docs/`**: Comprehensive architectural specifications, API contracts, integration guides, and environment instructions.

---

## Repository Structure

```
academic-os-handoff/
├── ai-service/          # Academic OS Python AI Engine (Tutor, RAG, ChromaDB, Personalization)
│   ├── src/             # Core learning intelligence modules
│   ├── infrastructure/  # LLMs, embeddings, Tavily search, Chroma vector store
│   ├── data/            # Demo profiles (student-001.json), uploads, chroma knowledge base
│   ├── tests/           # 280 automated tests (100% green)
│   ├── requirements.txt # Python dependency manifest
│   └── .env.example     # Safe AI service environment template
│
├── api/                 # Thin FastAPI Integration Facade
│   ├── main.py          # Application entrypoint & CORS middleware
│   ├── dependencies.py  # Auth token injection & AI module singleton
│   ├── schemas.py       # Pydantic v2 request/response models
│   └── routes/          # Health, Profile, Tutor, Materials, Study Tools, Assessments, Spaced Repetition
│
├── frontend/            # Production-Quality React Application
│   ├── src/
│   │   ├── api/         # Typed API clients for every backend endpoint
│   │   ├── context/     # StudentContext (auth-ready) & ToastContext
│   │   ├── components/  # Reusable AppShell, Citations, Selectors, Artifacts
│   │   └── pages/       # Dashboard, Tutor, MyLearning, Materials, StudyTools, Assessment, Profile, System
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
│
├── docs/                # Architecture, API Contracts, Integration Guides, OpenAPI
│   ├── ARCHITECTURE.md
│   ├── API_CONTRACT.md
│   ├── BACKEND_INTEGRATION_GUIDE.md
│   ├── FRONTEND_INTEGRATION_GUIDE.md
│   ├── ENVIRONMENT_SETUP.md
│   ├── KNOWN_ISSUES.md
│   └── openapi.json     # Complete generated OpenAPI 3.1.0 specification
│
├── README.md            # Root developer guide (this file)
└── .gitignore           # Git ignore rules for node_modules, .venv, caches, and secrets
```

---

## Core System Boundaries

- **React Frontend:** Pure presentation layer. Never computes concept mastery or grades assessments client-side. Passes exact course material selection (`null` for Trusted External, `[ids]` for Upload Mode).
- **Backend API:** Integration and authorization layer. Maps Bearer tokens or `X-Student-Id` headers to learner profiles and validates requests against Pydantic schemas.
- **Python AI Service:** Intelligence engine. Governs evidence retrieval, 0.80 trust thresholds, vector search, hierarchical personalization, and native artifact generation (`.pptx` / `.svg`).

---

## Quick Start: Local Run Instructions

### 1. Start the Backend API (Terminal 1)
```bash
# Create virtual environment & install requirements
python3 -m venv .venv
source .venv/bin/activate
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r ai-service/requirements.txt

# Configure environment
cp ai-service/.env.example ai-service/.env
# (Add your GEMINI_API_KEY and TAVILY_API_KEY in ai-service/.env)

# Run FastAPI backend facade
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Swagger UI available at: `http://localhost:8000/docs`

### 2. Start the React Frontend (Terminal 2)
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Open `http://localhost:5173` in your browser.

### 3. Run AI Test Suite (Terminal 3)
```bash
cd ai-service
pytest
```
*Result: 280 tests passed.*

---

## Railway production (URL for backend developer)

The API is packaged for [Railway](https://railway.app): `Dockerfile`, `railway.json`, `Procfile`, root `requirements.txt`.

1. Push this repo to GitHub.
2. New Railway project → deploy from GitHub → set variables from `.env.example` (`GEMINI_API_KEY`, `TAVILY_API_KEY`, `CORS_ORIGINS=*`).
3. Settings → Networking → **Generate Domain**.
4. Send the backend developer:

```
https://YOUR-SERVICE.up.railway.app
https://YOUR-SERVICE.up.railway.app/docs
https://YOUR-SERVICE.up.railway.app/openapi.json
```

Full steps: [`docs/RAILWAY_DEPLOY.md`](docs/RAILWAY_DEPLOY.md)  
Handoff sheet: [`docs/BACKEND_HANDOFF.md`](docs/BACKEND_HANDOFF.md)

---

## Primary API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Subsystem status (AI, vector store, search) |
| `GET` | `/capabilities` | 15 study tool kinds, 10 languages, provider modes |
| `GET` | `/students/{id}/profile` | Student profile, course, mastery matrix |
| `PATCH` | `/students/{id}/preferences` | Update learning style, language, course |
| `GET` | `/students/{id}/learning` | Aggregated learning state: Next Best Action, study plan, due reviews |
| `POST` | `/tutor/chat` | Evidence-grounded conversational AI tutor |
| `GET` | `/materials` | List uploaded course documents |
| `POST` | `/materials/upload` | Upload & index file into Chroma vector store |
| `POST` | `/study-tools/generate` | Generate study tools (flashcards, SVG diagram, PPTX deck) |
| `POST` | `/assessments/generate` | Generate diagnostic knowledge check |
| `POST` | `/assessments/{id}/submit` | Submit answers for server grading & mastery updates |
| `POST` | `/spaced-repetition/review` | Record 'Remembered' or 'Forgot' review feedback |
| `GET` | `/artifacts/{id}/download` | Download generated `.pptx` or `.svg` files |

---

## Key Invariants Preserved

1. **Evidence Grounding:** 0% model-memory hallucination. Factually unsupported claims are either omitted with an explicit **Evidence Limitation Notice** or safely refused.
2. **Trust Threshold:** Non-negotiable `0.80` threshold strictly filters out SEO commercial blog posts and unverified content.
3. **Hierarchical Personalization:** Adapts pedagogical depth per concept (Mastered Strength = concise higher-level treatment; Missing Knowledge = first-principles foundational scaffolding; Weak Concept = targeted reinforcement with error contrast).
4. **Embedding Compatibility:** `intfloat/multilingual-e5-small` (dimension 384) verified matching ChromaDB collection `academic_knowledge` (count 3,153).
5. **Zero Secret Leakage:** No API keys or secrets are exposed to the client or checked into git.
