# Architecture

## System boundary

The host university platform owns authentication, accounts, roles, enrollment, global navigation, and the production frontend/backend shell. This repository owns tutoring, trusted RAG, learner intelligence, assessment, multilingual processing, personalization, content generation, model routing, and learning orchestration.

## Runtime architecture

```text
Host Platform
    ↓
LearningIntelligenceModule facade
    ↓
AITutor / Learning Orchestration
    ├── LanguageService
    ├── QueryAnalyzer
    ├── SourceStrategyPlanner
    ├── TrustedDiscoveryService
    │     └── Search Provider → Trust Registry → Safe Web Fetch
    ├── Shared Ingestion + Vector Store
    ├── Hybrid Retrieval + Evidence Gate
    ├── Grounded LLM Providers
    ├── AssessmentService
    ├── Persistent StudentProfile
    ├── PersonalizationService
    ├── Next Best Action
    └── ContentGenerator + ModelRouter
```

## A. Uploaded-material question

Upload → safe filename/size/type validation → extraction → cleaning → chunking → embeddings → persistent index. A selected document or explicit source-constrained query retrieves only student-upload chunks. If evidence is irrelevant or insufficient, the system hard-abstains and never falls back to model memory.

## B. General trusted question

Question → English normalized query → source strategy planning → trusted search → URL/domain trust validation → safe public-network fetch → text/PDF extraction and cleaning → trusted-external chunks → persistent index → hybrid semantic/BM25/RRF retrieval → evidence gate → personalized grounded synthesis → citations. If search is unavailable or evidence remains insufficient, the system abstains.

## C. Multilingual question

Original query is retained → language/variant detection → English normalization/translation → source/retrieval pipeline → grounded English internal answer → translated back to original language. Code, citations, technical identifiers, equations, URLs, and filenames are protected.

## D. Assessment

Topic/concepts → diagnostic questions → localized I-don't-know handling → deterministic objective grading + conservative semantic free-text grading → misconception detection → evidence-weighted mastery/confidence update → persistent assessment history.

## E. Personalized content

Learner profile → content-context adapter → Next Best Action → weak/misconception target selection → trusted external evidence → per-resource capability routing → generation → validation state/artifact → persistence.

## F. Multi-model generation

The ModelRouter scores only configured providers by task capability and language fit. Runtime execution records selected provider/model and success/failure in an internal execution trace. Multi-provider mode is true only when at least two real providers are configured. No provider is credited unless its adapter is actually invoked.

## Shared knowledge layer

Both uploaded and trusted external sources are stored through the same ingestion/vector interfaces. Retrieval uses explicit document IDs to prevent accidental mixing. Student-owned uploaded documents and fetched trusted evidence are isolated by student owner ID in the demo runtime.