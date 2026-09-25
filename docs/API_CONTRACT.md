# Academic OS API Contract & Specification

This document specifies the REST API exposed by the thin backend integration facade (`api/main.py`). The full interactive specification is available at `GET /docs` and `GET /openapi.json`.

---

## Base URLs & Headers

- **Default Local URL:** `http://localhost:8000`
- **Authentication Headers (Auth-Ready):**
  - `Authorization: Bearer <token>`
  - `X-Student-Id: <student_id>` (optional fallback; defaults to `student-001` in demo mode)
- **Standard Content-Type:** `application/json` (except `/materials/upload` and `/tutor/voice` which use `multipart/form-data`)

---

## 1. System & Health

### `GET /health`
Returns runtime status of all AI subsystems, vector store, and search providers.

**Response (200 OK):**
```json
{
  "status": "ok",
  "ai_status": {
    "llm_provider": "gemini",
    "embedding_provider": "intfloat/multilingual-e5-small",
    "vector_store": "ChromaDB (count: 3153)",
    "storage": "persistent JSON (atomic writes)",
    "trusted_search_available": true
  }
}
```

### `GET /capabilities`
Lists system capabilities, supported content generation kinds, and languages.

**Response (200 OK):**
```json
{
  "active_providers": ["gemini", "tavily"],
  "content_types": [
    "explanation", "summary", "notes", "study_guide", "flashcards",
    "quiz", "exam", "practice", "code", "coding_exercise",
    "diagram", "presentation", "analogy", "comparison", "question_bank"
  ],
  "languages": ["en", "ar", "fr", "sw", "ha", "am", "so", "yo", "ig", "zu"],
  "neural_embeddings": true
}
```

---

## 2. Student Profile & Learning State

### `GET /students/{student_id}/profile`
Retrieves student profile, course context, and concept mastery matrix.

**Response (200 OK):**
```json
{
  "student_id": "student-001",
  "name": "Demo Student",
  "course": "Algorithms and Data Structures",
  "preferred_language": "en",
  "learning_preference": "step-by-step",
  "concept_mastery": {
    "Binary search": 1.0,
    "binary search trace": 1.0,
    "worst-case complexity": 0.0,
    "space complexity": 0.0
  },
  "weak_concepts": ["worst-case complexity", "space complexity"],
  "unknown_concepts": ["worst-case complexity"],
  "strengths": ["Binary search", "binary search trace"]
}
```

### `PATCH /students/{student_id}/preferences`
Updates student learning style, course, or preferred language.

**Request Body:**
```json
{
  "name": "Alex Carter",
  "course": "Computer Science",
  "preferred_language": "en",
  "learning_preference": "step-by-step"
}
```

### `GET /students/{student_id}/learning`
Returns aggregated learning intelligence: Next Best Action, study plan, and due spaced reviews.

**Response (200 OK):**
```json
{
  "profile": { ... },
  "next_action": {
    "action": "build_foundation",
    "reason": "Missing knowledge was identified from assessment evidence; foundational learning is required.",
    "target_concepts": ["worst-case complexity"],
    "strategy": "foundational",
    "recommended_resources": ["explanation", "diagram", "study_guide"],
    "priority": "high"
  },
  "study_plan": [
    {
      "title": "Build Foundation: worst-case complexity",
      "concept": "worst-case complexity",
      "priority": "high",
      "reason": "Missing knowledge was identified from assessment evidence.",
      "recommended_actions": ["Ask Tutor for introduction", "Generate Study Guide"],
      "completed": false
    }
  ],
  "review_queue": [
    {
      "concept": "worst-case complexity",
      "due_date": "2026-09-24T12:00:00Z",
      "interval_days": 1.0,
      "repetition": 0,
      "ease_factor": 2.5,
      "mastery": 0.0
    }
  ]
}
```

---

## 3. AI Tutor

### `POST /tutor/chat`
Conversational learning endpoint with strict evidence grounding.

**Request Body:**
```json
{
  "student_id": "student-001",
  "course_id": "Algorithms and Data Structures",
  "message": "Explain how binary search works, including its required input condition, decision process, worst-case time complexity, and iterative space complexity.",
  "language": "en",
  "document_ids": null,
  "tutoring_style": "direct",
  "session_id": "web-session"
}
```

*Note on `document_ids`:*
- `null` or `[]` = **Mode B: Trusted External Discovery** (searches verified university notes via Tavily; trust threshold 0.80).
- `["doc-123", ...]` = **Mode A: Selected Course Materials** (strictly queries uploaded documents; zero external search).

**Response (200 OK):**
```json
{
  "answer": "Binary search requires that the array must be sorted [1]...",
  "evidence": [
    {
      "citation_id": "cite-1",
      "source": "Carnegie Mellon University 15-122 Principles of Imperative Computation",
      "source_type": "trusted_external",
      "authority": "university",
      "trust_score": 0.98,
      "url": "https://www.cs.cmu.edu/~fp/courses/15122-f10/lectures/06-binsearch.pdf",
      "page": 2,
      "excerpt": "For binary search to work correctly, the array must be sorted..."
    }
  ],
  "abstained": false,
  "search_state": "found_external",
  "source_type": "trusted_external",
  "evidence_limitation": "The retrieved evidence grounds the core mechanics, but auxiliary space complexity bounds were omitted.",
  "diagnostics": {}
}
```

---

## 4. Course Materials

### `GET /materials`
Lists all uploaded documents.

**Query Parameters:**
- `student_id`: string (required)
- `course`: string (optional)

### `POST /materials/upload`
Uploads and indexes a document (.txt, .md, .pdf, .docx, .pptx).

**Request (`multipart/form-data`):**
- `file`: binary file
- `course`: string
- `student_id`: string

**Response (200 OK):**
```json
{
  "document_id": "3b29c908-1123-4fae-b210-908129012384",
  "filename": "lecture1_algorithms.pdf",
  "course": "Algorithms",
  "chunk_count": 8,
  "status": "indexed",
  "message": "Material successfully uploaded and indexed into knowledge base."
}
```

---

## 5. Study Tools Generation

### `POST /study-tools/generate`
Generates one or multiple study tools from the 15 supported kinds.

**Request Body:**
```json
{
  "student_id": "student-001",
  "topic": "Binary Search",
  "kinds": ["explanation", "flashcards", "diagram", "presentation"],
  "language": "en",
  "document_ids": null
}
```

**Response (200 OK):**
```json
{
  "topic": "Binary Search",
  "resources": {
    "explanation": {
      "type": "text",
      "kind": "explanation",
      "content": "...",
      "sources": ["CMU 15-122 Lecture 6"],
      "learner_state": "strength"
    },
    "diagram": {
      "type": "file",
      "kind": "diagram",
      "filename": "binary_search_22ef0385.svg",
      "download_url": "/artifacts/binary_search_22ef0385.svg/download",
      "mime_type": "image/svg+xml",
      "content": "<svg ...></svg>"
    },
    "presentation": {
      "type": "file",
      "kind": "presentation",
      "filename": "binary_search_6f4be19c.pptx",
      "download_url": "/artifacts/binary_search_6f4be19c.pptx/download",
      "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    }
  }
}
```

---

## 6. Diagnostic Assessments

### `POST /assessments/generate`
Generates a formative knowledge check.

**Request Body:**
```json
{
  "student_id": "student-001",
  "topic": "Binary Search",
  "language": "en",
  "document_ids": null
}
```

### `POST /assessments/{assessment_id}/submit`
Submits student answers for server-side grading and mastery update.

**Request Body:**
```json
{
  "student_id": "student-001",
  "answers": {
    "q-1": "The array must be strictly sorted.",
    "q-2": "I don't know"
  },
  "language": "en"
}
```

**Response (200 OK):**
```json
{
  "assessment_id": "assessment-abc",
  "score": 0.5,
  "concept_mastery": {
    "worst-case complexity": 0.0,
    "space complexity": 1.0
  },
  "weak_concepts": ["worst-case complexity"],
  "unknown_concepts": ["worst-case complexity"],
  "strengths": ["space complexity"],
  "recommendations": ["Learn worst-case complexity from the fundamentals."],
  "feedback_per_question": {
    "q-1": {
      "concept": "precondition",
      "student_answer": "The array must be strictly sorted.",
      "expected_answer": "The array must be strictly sorted.",
      "is_correct": true,
      "is_idk": false,
      "rubric": "Array must be sorted."
    }
  }
}
```

---

## 7. Spaced Repetition

### `POST /spaced-repetition/review`
Records a review result (`remembered: true/false`).

**Request Body:**
```json
{
  "student_id": "student-001",
  "concept": "worst-case complexity",
  "remembered": true
}
```

---

## 8. Artifacts

### `GET /artifacts/{artifact_id}/download`
Downloads generated binary artifacts (`.pptx`, `.svg`, `.docx`, `.pdf`).
