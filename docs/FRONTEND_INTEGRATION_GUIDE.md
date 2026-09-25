# Frontend Integration & Developer Guide: Academic OS

## Overview

The Academic OS frontend is built with React 19, Vite, TypeScript, React Router v7, and TanStack Query v5. It is designed as a presentation-only client layer that visualizes evidence-grounded learning without replicating backend logic.

---

## 1. Directory Structure

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── .env.example
├── src/
│   ├── api/             # Typed API clients for every backend module
│   │   ├── client.ts    # Central fetch wrapper with auth header injection
│   │   ├── endpoints.ts # Endpoint URL constants
│   │   ├── types.ts     # TypeScript interfaces matching backend models
│   │   ├── tutor.ts
│   │   ├── materials.ts
│   │   ├── studyTools.ts
│   │   ├── assessments.ts
│   │   ├── learning.ts
│   │   ├── profile.ts
│   │   └── spacedRepetition.ts
│   ├── context/         # React Contexts
│   │   ├── StudentContext.tsx # Centralized student identity & active profile
│   │   └── ToastContext.tsx   # Global notification toasts
│   ├── components/      # Reusable UI component library
│   │   ├── layout/      # AppShell, Sidebar, TopNavigation, PageHeader
│   │   ├── common/      # Badges, Selectors, Citations, Error/Empty states
│   │   └── study/       # Flashcards, Artifact preview, Question banks
│   ├── pages/           # Route views
│   │   ├── Dashboard.tsx
│   │   ├── TutorPage.tsx
│   │   ├── MyLearningPage.tsx
│   │   ├── MaterialsPage.tsx
│   │   ├── StudyToolsPage.tsx
│   │   ├── AssessmentPage.tsx
│   │   ├── ProfilePage.tsx
│   │   └── SystemPage.tsx
│   └── utils/           # Localization (i18n) & formatters
```

---

## 2. Environment Variables

Configure `frontend/.env`:

```env
# Backend API Base URL (no trailing slash)
VITE_API_BASE_URL=http://localhost:8000

# Local demo student ID fallback (replaced by real auth in production)
VITE_DEMO_STUDENT_ID=student-001
```

**Security Warning:** Never expose LLM API keys (`GEMINI_API_KEY`, `TAVILY_API_KEY`) in Vite environment variables. All AI reasoning and keys remain strictly on the backend.

---

## 3. Student & Auth Context (`useStudent`)

All components consume student identity through the `useStudent()` hook:

```tsx
import { useStudent } from '../context/StudentContext';

export const MyComponent = () => {
  const { studentId, profile, language, setLanguage, updatePreferences } = useStudent();
  // ...
};
```

When integrating user authentication (e.g., Supabase, Auth0, Firebase):
1. Obtain the JWT token after login.
2. Call `setToken(jwtToken)` in `StudentContext.tsx`.
3. The API client will automatically inject `Authorization: Bearer <token>` into all outbound requests.

---

## 4. UI Guidelines & Component Conventions

### Evidence Scope Selector (`<MaterialSelector />`)
- When `selectedIds` is empty (`[]`), the backend runs in **Trusted External Mode** (Mode B).
- When `selectedIds` has items, the backend runs in **Source-Constrained Upload Mode** (Mode A).
- The frontend component emits changes directly to parent state, passing `null` or the array to the API.

### Grounding & Citations (`<CitationCard />`)
- Only render citations returned by the backend under `response.evidence`.
- Never fabricate citations or source numbers client-side.
- If `evidence_limitation` is present in the response, render the `<EvidenceLimitation />` callout prominently.

### Study Tool Artifacts (`<ArtifactPreview />`)
- SVG diagrams are previewed inline via secure HTML rendering with responsive boundaries.
- PowerPoint slide decks (`.pptx`) provide a dedicated download button that requests `/artifacts/{filename}/download`.

---

## 5. Local Development Commands

```bash
cd frontend
npm install
npm run dev      # Starts Vite dev server on http://localhost:5173
npm run build    # Compiles TypeScript and builds production assets to dist/
npm run lint     # Runs oxlint static analysis
```
