# Academic OS System Architecture

## Overview

Academic OS is an AI-powered personalized academic learning and intelligence platform designed to replace ungrounded LLM guessing with verified, citation-backed knowledge. It combines course material ingestion, live trusted external retrieval, pedagogical personalization, and automated study tool generation.

```
┌─────────────────────────────────────────────────────────────────┐
│                    React Client Layer (SPA)                     │
│  - Vite + TypeScript + React Router v7 + TanStack Query v5      │
│  - Tailwind CSS Modern EdTech SaaS Component System             │
│  - Auth-Ready Student Context (Bearer Token + X-Student-Id)     │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP / JSON / OpenAPI
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Thin Backend API Facade (FastAPI)                  │
│  - api/main.py: CORS, standard error responses, routing        │
│  - api/routes/: health, profile, tutor, materials, study-tools, │
│                 assessments, spaced-repetition, artifacts       │
│  - api/dependencies.py: Auth resolver, singleton AI facade      │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Python In-Process Facade
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│         Academic OS AI Engine (ai-service/src)                  │
│  ┌───────────────────────────┐  ┌─────────────────────────────┐ │
│  │ LearningIntelligenceModule│  │ AI Tutor Orchestrator       │ │
│  │ (Integration Facade)      │  │ (Hierarchical Personalizer) │ │
│  └─────────────┬─────────────┘  └──────────────┬──────────────┘ │
│                │                               │                │
│  ┌─────────────▼─────────────┐  ┌──────────────▼──────────────┐ │
│  │ Retrieval & Discovery     │  │ Grounding & Verification    │ │
│  │ - Mode A: Uploaded (k=8)  │  │ - 0.80 Trust Threshold      │ │
│  │ - Mode B: Trusted Search  │  │ - Partial Coverage Policy   │ │
│  │ - BM25 + Vector Hybrid    │  │ - Exact Citation Mapping    │ │
│  └─────────────┬─────────────┘  └──────────────┬──────────────┘ │
│                │                               │                │
│  ┌─────────────▼─────────────┐  ┌──────────────▼──────────────┐ │
│  │ Content Generation        │  │ Student Intelligence        │ │
│  │ - 15 Study Tool Kinds     │  │ - Next Best Action (NBA)    │ │
│  │ - python-pptx & SVG       │  │ - Spaced Repetition (SM-2)  │ │
│  │ - Strict Template Bounds  │  │ - Diagnostic Assessments    │ │
│  └───────────────────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architectural Principles & Strict Boundaries

### 1. Presentation Layer (React Frontend)
- **Role:** Pure presentation and client-state management.
- **Rules:**
  - Never calculates or updates concept mastery client-side.
  - Never grades assessment answers client-side.
  - Never invents fallback answers or analogies from client memory.
  - Passes exact course material selection (`null` = Mode B Trusted External; `[id1, ...]` = Mode A Upload).
  - Handles safe refusals, partial evidence notices, and error states gracefully.

### 2. Integration Layer (Backend / FastAPI Facade)
- **Role:** Boundary between web clients and the AI intelligence engine.
- **Rules:**
  - Enforces request validation using Pydantic v2 schemas.
  - Manages authentication integration (Bearer token mapping to `student_id`).
  - Serializes domain contracts cleanly to JSON.
  - Exposes interactive Swagger (`/docs`) and machine-readable OpenAPI (`/openapi.json`).

### 3. AI Intelligence Layer (Academic OS Python)
- **Role:** Autonomous reasoning, search, retrieval, validation, and pedagogy.
- **Subsystems:**
  - **Tutor / Conversational AI:** Formulates responses grounded in evidence.
  - **Trusted External RAG:** Queries university lecture notes and textbooks via Tavily; enforces strict `0.80` trust threshold.
  - **Upload Mode RAG:** Performs hybrid BM25 + dense embedding retrieval strictly against student uploaded course documents.
  - **Grounding Validator:** Evaluates factual overlap, prevents ungrounded hallucination, and inserts evidence limitation notices.
  - **Personalization Engine:** Adapts pedagogical depth hierarchically based on parent topic vs. subconcept mastery status (`strength`, `weak_attempted`, `missing_knowledge`).
  - **Content Generation:** Generates all 15 study resource types including native PPTX slide decks and SVG diagrams.
  - **Diagnostic Assessments:** Generates formative knowledge checks with explicit *"I don't know"* tracking.
