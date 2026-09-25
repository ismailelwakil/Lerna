# Academic OS — Pre-Manual Feature Verification Matrix

This matrix documents the comprehensive feature verification of Academic OS (`/home/user/academic-os`) prior to human acceptance testing. Every feature listed has been statically traced to implementation and automatically verified via integration test suites.

## Status Legend
- **PASS**: Verified working through automated integration / boundary tests.
- **BLOCKED**: External live provider credentials unavailable (degrades gracefully with honest capability reporting).
- **NOT APPLICABLE (N/A)**: Not applicable for this specific tier (e.g. internal backend infrastructure not directly exposed in UI).

---

## 1. Runtime & Platform

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Settings & Config | `src/core/config.py` | Built-in | `/health` | Configured | Env / Defaults | `tests/unit/test_core.py` | Internal | **PASS** |
| JSON Storage & Locking | `infrastructure/storage/json_store.py` | `AITutor.store` | N/A | Cached | Atomic File Lock | `tests/unit/test_hardening.py` | Internal | **PASS** |
| System Factory DI | `src/orchestration/factory.py` | `build_system()` | N/A | App init | Runtime graph | `tests/e2e/test_flows.py` | Internal | **PASS** |
| Integration Facade | `src/integration/service.py` | `LearningIntelligenceModule` | Internal | Core engine | Store bridge | `tests/integration/test_module_facade.py` | Student-facing | **PASS** |
| Content Creation API | `source_modules/.../app/main.py` | FastAPI app | 27 endpoints | N/A | DB / Worker | `source_modules/.../tests/test_unit.py` | Internal / Service | **PASS** |
| Streamlit User Interface | `app/streamlit_app.py` | UI frontend | Starlette | Port 8501 | Session State | `tests/unit/test_student_ui_contract.py` | Student-facing | **PASS** |
| Capability Honesty | `AITutor.supported_capabilities` | `get_supported_capabilities()` | `/internal/health`| Status Expander | Dynamic | `tests/pre_manual/test_pre_manual_regressions.py` | Student-facing | **PASS** |
| Health Liveness | `AITutor.health()` | `health()` | `/health` | Header status | Dynamic | `tests/e2e/test_flows.py` | Internal | **PASS** |

---

## 2. Identity & Isolation

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Student Identity | `src/contracts/models.py` | `sync_learning_context` | `/from-document` | Student Header | Disk JSON | `tests/e2e/test_flows.py` | Student-facing | **PASS** |
| Course Scoping | `src/contracts/models.py` | `course` parameter | Metadata | Course Selector | Disk JSON | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Session Management | `StudentQuery.session_id` | `ask_tutor` | Job Context | Session State | Ephemeral/Store | `tests/e2e/test_flows.py` | Student-facing | **PASS** |
| Cross-Student Isolation | Vector store & Storage | `retrieve()`, `list_chunks` | Document routes | App context | Scoped keys | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Conversation History | `StudentProfile.conversation_history` | `get_learning_profile` | N/A | Chat messages | Disk JSON | `tests/e2e/test_flows.py` | Student-facing | **PASS** |
| Restart Persistence | `src/orchestration/factory.py` | `create_or_load_student` | DB init | Page reload | Atomic JSON | `tests/e2e/test_flows.py` | Student-facing | **PASS** |

---

## 3. Document Intelligence

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| PDF Extraction | `pypdf` loader | `upload_course_material` | `/documents/upload`| File uploader | Vector Store | `tests/integration/test_ingestion.py` | Student-facing | **PASS** |
| DOCX Table Extraction | `python-docx` loader | `upload_course_material` | `/documents/upload`| File uploader | Vector Store | `tests/integration/test_ingestion.py` | Student-facing | **PASS** |
| PPTX Text/Shape Extraction | `python-pptx` loader | `upload_course_material` | `/documents/upload`| File uploader | Vector Store | `tests/integration/test_ingestion.py` | Student-facing | **PASS** |
| Plain Text / Markdown | UTF-8 reader | `upload_course_material` | `/documents/upload`| File uploader | Vector Store | `tests/integration/test_ingestion.py` | Student-facing | **PASS** |
| Content Deduplication | SHA-256 fingerprinting | `upload_course_material` | Manifest check | Upload notice | Manifest JSON | `tests/integration/test_retrieval_hybrid.py` | Internal | **PASS** |
| Chunking & Provenance | `src/ingestion/service.py` | `list_course_materials` | `/documents/{id}` | Material cards | Vector Store | `tests/integration/test_ingestion.py` | Student-facing | **PASS** |
| Textless Scanned PDF Error | `PDFLoader.load()` | Native exception | Error envelope | Error banner | N/A | `tests/integration/test_ingestion.py` | Student-facing | **PASS** |

---

## 4. Embeddings & Vector Store

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| SentenceTransformers MiniLM | `SentenceTransformerEmbeddingProvider` | Built-in | Vector Store | Embedding layer | Memory/PyTorch | `scripts/smoke_test.py` | Internal | **PASS** |
| Fallback Embeddings | `DeterministicEmbeddingProvider` | Factory fallback | Memory | Embed Double | Test mode | `tests/unit/test_chroma_adapter.py` | Internal | **PASS** |
| Local Cosine Vector Store | `LocalVectorStore` | Retrieval service | Local index | Vector query | `index.json` | `tests/integration/test_retrieval_hybrid.py` | Internal | **PASS** |
| Chroma Vector Store | `ChromaVectorStore` | Retrieval service | Chroma Client | Optional DB | SQLite/Chroma | `tests/unit/test_chroma_adapter.py` | Optional capability | **PASS** |
| Vector Metadata Filtering | `owner_id`, `course` filters | Query filters | Scoped queries | Materials Multiselect | Vector index | `tests/integration/test_master_regression.py` | Internal | **PASS** |

---

## 5. Retrieval Intelligence

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| BM25 Lexical Ranking | `rank_bm25` | `retrieval.retrieve` | Search engine | Evidence fetch | Token index | `tests/integration/test_retrieval_hybrid.py` | Internal | **PASS** |
| Dense Vector Semantic Search | Cosine similarity | `retrieval.retrieve` | Similarity | Evidence fetch | Vector embeddings | `tests/integration/test_retrieval_hybrid.py` | Internal | **PASS** |
| Hybrid RRF Fusion | Reciprocal Rank Fusion | `retrieval.retrieve` | Ranked results | Ranked evidence | Dynamic scoring | `tests/integration/test_retrieval_hybrid.py` | Internal | **PASS** |
| Domain Dynamic Weighting | Medical / Tech / Econ weights | `retrieval.retrieve` | Domain routing | Tuned scoring | Configuration | `tests/integration/test_master_regression.py` | Internal | **PASS** |
| Semantic Near-Miss Filter | `is_semantic_near_miss` | `retrieval.retrieve` | Safe filter | Cleaned evidence | Dynamic check | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Relevance Gating | Trust score >= 0.80 check | `retrieval.retrieve` | Relevance gate | Sufficiency check | Dynamic gate | `tests/integration/test_trusted_multilingual_flow.py` | Student-facing | **PASS** |

---

## 6. Trusted External Search

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Directive Normalization | `clean_query_for_search` | Search query | Cleaned string | Auto-cleaned | Query pipeline | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Multi-domain Registry | `AUTHORITATIVE_DOMAINS` | `source_tier`, `trust` | Domain filter | Evidence badges | Static Registry | `tests/integration/test_master_regression.py` | Internal | **PASS** |
| Wikipedia Policy Gate | Excluded if Tier A exists | Evidence selection | Exclusion filter | Filtered sources | Dynamic policy | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Clinical Wikipedia Rejection | Medical domain exclusion | High-stakes filter | Rejection gate | Filtered sources | Dynamic policy | `tests/integration/test_student_journeys.py` | Student-facing | **PASS** |
| Tavily Search Provider | `TavilyTrustedSearch` | `discovery.discover` | Web query | External search | Web fetch | `scripts/trusted_search_smoke.py` | External-provider | **PASS** |
| Mock Search Knowledge | `MockTrustedSearch` | Offline discovery | Double | Test fixtures | Curated registry | `tests/integration/test_master_regression.py` | Internal | **PASS** |

---

## 7. Grounded Generation & Citations

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Structured Synthesis | Definition + Mechanism + Comp | `ask_tutor` | `/explain` | Formatted Answer | Dynamic LLM | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Bracketed Citations | `validator.citations()` | `TutorResponse.citations` | Source list | Citation cards | Response object | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Honest Abstention | Insufficient evidence refusal | `TutorResponse.abstained` | Explicit refusal | Warning banner | Response object | `tests/e2e/test_flows.py` | Student-facing | **PASS** |
| Contradiction Warning | Divergent claims detection | `conflict_detected` | Warning notice | Conflict callout | Response object | `tests/e2e/test_flows.py` | Student-facing | **PASS** |
| One-Sentence Constraint | Directive adherence | Direct synthesis | Single line | Terse answer | Response object | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |

---

## 8. Provider Routing & Resilience

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Multi-Provider Router | `ModelRouter` | Capability mapping | Provider select | Provider status | Configuration | `tests/unit/test_router_truthfulness.py` | Internal | **PASS** |
| Google Gemini Live | `GeminiProvider` | Live LLM | Generation | Active model | Cloud API | `scripts/provider_smoke.py` | External-provider | **PASS** |
| OpenAI Provider | `OpenAIProvider` | Fallback LLM | Generation | Configured | Cloud API | `scripts/provider_smoke.py` | External-provider | **BLOCKED** (Quota) |
| Anthropic Claude Provider | `AnthropicProvider` | Fallback LLM | Generation | Configured | Cloud API | `scripts/provider_smoke.py` | External-provider | **BLOCKED** (Credit) |
| Groq Llama Provider | `GroqProvider` | Fast LLM | Generation | Configured | Cloud API | `scripts/provider_smoke.py` | External-provider | **BLOCKED** (Unconfigured) |
| Safe Provider Failover | Candidate loop in `AITutor` | `_generate_with_failover` | Error wrapper | Clean fallback | Failover cache | `tests/e2e/test_flows.py` | Internal | **PASS** |
| Traceback / Secret Shield | `ProviderError` wrapper | No secret exposure | Clean envelope | Error toast | Safe logging | `tests/security/test_url_security.py` | Internal | **PASS** |

---

## 9. Multilingual Intelligence

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| African/ME Detection (10) | `LanguageService.detect` | Language detection | Auto-detect | Language chips | LanguageResult | `tests/unit/test_core.py` | Student-facing | **PASS** |
| Egyptian Arabic Adaptation | `dialectal_arabic` handler | Normalization | RTL query | Arabic answers | Dialect state | `tests/integration/test_student_journeys.py` | Student-facing | **PASS** |
| Code-Switching Preservation | Latin term preservation | Normalized query | Bilingual text | Bilingual chat | Term regex | `tests/unit/test_core.py` | Student-facing | **PASS** |
| Concept Mastery Identity | Unified concept keying | Mastery tracking | Multilingual | Profile state | Disk JSON | `tests/e2e/test_flows.py` | Student-facing | **PASS** |
| Direction & Script Detection | RTL / LTR script mapping | Direction helper | Localization | CSS Direction | LanguageResult | `tests/unit/test_hardening.py` | Student-facing | **PASS** |

---

## 10. AI Tutor Tutoring Modes

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Direct Mode | Factual full answer | `ask_tutor` | `/explain` | Radio: Direct | Session context | `tests/e2e/test_flows.py` | Student-facing | **PASS** |
| Socratic Guidance Mode | Guiding inquiry prompts | `ask_tutor` | Scaffolding | Radio: Socratic | Session context | `tests/e2e/test_flows.py` | Student-facing | **PASS** |
| Course-Constrained Tutoring | Material filtering | `document_ids` param | `/from-document` | Materials dropdown | Document store | `tests/integration/test_student_journeys.py` | Student-facing | **PASS** |
| Trusted General Discovery | Web external discovery | `ask_tutor` | External search | Unselected state | External cache | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Conversational Memory | Recent topics & history | `get_learning_profile` | History buffer | Chat thread | Disk JSON | `tests/e2e/test_flows.py` | Student-facing | **PASS** |

---

## 11. Learner Intelligence & Mastery

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Concept Mastery Engine | Dynamic score tracking | `get_learning_profile` | Context state | Mastery Bar Chart | Disk JSON | `tests/e2e/test_flows.py` | Student-facing | **PASS** |
| Knowledge Gap Detection | Weak concepts (<0.60) | `get_learning_profile` | Focus areas | Focus next list | Disk JSON | `tests/test_integrated_learning_cycle.py` | Student-facing | **PASS** |
| Misconception Detection | Hard misconception regex | Diagnostic analysis | Misconceptions | Revisit warning | Disk JSON | `tests/test_integrated_learning_cycle.py` | Student-facing | **PASS** |
| Misconception Clearance | Resolution upon mastery | `submit_diagnostic` | Resolved state | Cleared success | Disk JSON | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Exposure & Confidence Tracking | Frequency & confidence | `get_learning_profile` | Metadata | Analytics card | Disk JSON | `tests/pre_manual/test_pre_manual_regressions.py` | Student-facing | **PASS** |

---

## 12. Assessment & Diagnostics

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Diagnostic Generation | MCQ / Short / True-False | `create_diagnostic` | `/quiz` | Knowledge Check form | Assessment object | `tests/test_integrated_learning_cycle.py` | Student-facing | **PASS** |
| Explicit "I Don't Know" | Multilingual IDK mapping | Form options | Unassessed flag | IDK option choice | Assessment history | `tests/unit/test_assessment_idk.py` | Student-facing | **PASS** |
| Automated Scoring & Partial | Formulas, MCQ letters, math | `submit_diagnostic` | Scoring engine | Score display | Assessment history | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Reassessment Flow | Mastery recovery | `submit_diagnostic` | Progress check | Dynamic rerun | Disk JSON | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |

---

## 13. Personalization & Next Best Action

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Next Best Action Engine | Priority-ordered actions | `get_next_learning_action` | Action guidance | NBA Card | Dynamic engine | `tests/test_integrated_learning_cycle.py` | Student-facing | **PASS** |
| Remediate Prerequisite Action | Triggered by gap | Next action | Scaffolding | Focus list | Profile state | `tests/test_integrated_learning_cycle.py` | Student-facing | **PASS** |
| Correct Misconception Action | Triggered by misconception | Next action | Contrastive plan | Revisit warning | Profile state | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Targeted Practice / Progress | Triggered by mastery | Next action | Challenge plan | Next steps | Profile state | `tests/test_integrated_learning_cycle.py` | Student-facing | **PASS** |
| Learning Style Adaptation | Step-by-step, visual, code | Strategy selection | Pedagogy | Profile preferences | Profile state | `tests/e2e/test_flows.py` | Student-facing | **PASS** |

---

## 14. Learning Optimization

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Spaced Repetition Scheduler | SM-2 intervals & half-life | `get_review_queue` | Review items | Due Review List | Disk JSON | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Review Queue Recall Actions | Remembered / Forgot logging | `record_concept_review` | Log review | Interactive buttons | Profile update | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Reactive Study Planner | Priority-ranked study plan | `get_study_plan` | Plan items | Study Plan Accordion | Disk JSON | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |

---

## 15. Content Generation (All 15 Declared Types)

| Content Type | Backend | Facade | API Route | Streamlit | Artifact Form | Automated Test | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `explanation` | Content Service | `generate_learning_resources` | `/explain` | Markdown | Text | `tests/integration/test_master_regression.py` | **PASS** |
| `summary` | Content Service | `generate_learning_resources` | `/summarize` | Markdown | Text | `tests/integration/test_master_regression.py` | **PASS** |
| `notes` | Content Service | `generate_learning_resources` | `/notes` | Markdown | Text | `tests/integration/test_master_regression.py` | **PASS** |
| `study_guide` | Content Service | `generate_learning_resources` | `/study-guide` | Markdown | Text | `tests/integration/test_master_regression.py` | **PASS** |
| `flashcards` | Content Service | `generate_learning_resources` | `/flashcards` | Q&A Cards | Text | `tests/integration/test_master_regression.py` | **PASS** |
| `quiz` | Content Service | `generate_learning_resources` | `/quiz` | Interactive Qs | Text | `tests/integration/test_master_regression.py` | **PASS** |
| `exam` | Content Service | `generate_learning_resources` | `/exam` | Formal Exam | Text | `tests/integration/test_master_regression.py` | **PASS** |
| `practice` | Content Service | `generate_learning_resources` | `/practice` | Problem Set | Text | `tests/integration/test_master_regression.py` | **PASS** |
| `code` | Content Service | `generate_learning_resources` | `/examples` | Code block | Code | `tests/integration/test_master_regression.py` | **PASS** |
| `coding_exercise` | Content Service | `generate_learning_resources` | `/examples` | Exercise scaffold | Code | `tests/integration/test_master_regression.py` | **PASS** |
| `diagram` | SVG Generator | `generate_learning_resources` | `/diagram` | In-line SVG / DL | File (SVG) | `tests/integration/test_master_regression.py` | **PASS** |
| `presentation` | PPTX Generator | `generate_learning_resources` | Slides export | DL Button | File (PPTX) | `tests/integration/test_master_regression.py` | **PASS** |
| `analogy` | Content Service | `generate_learning_resources` | Analogy prompt | Markdown | Text | `tests/integration/test_master_regression.py` | **PASS** |
| `comparison` | Content Service | `generate_learning_resources` | Table prompt | Markdown Table | Text | `tests/integration/test_master_regression.py` | **PASS** |
| `question_bank` | Content Service | `generate_learning_resources` | `/question-bank`| Taxonomy list | Text | `tests/integration/test_master_regression.py` | **PASS** |
| Artifact Download & Storage | Disk Writer | File artifacts | Assets route | Download Buttons | File System | `tests/e2e/test_resources.py` | **PASS** |

---

## 16. Voice Tutor

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Audio Header Validation | RIFF/MP3/OGG byte check | Voice service | Content-Type | Push-to-Talk | Temp file | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Audio Size Guard (10MB) | Length guard | Voice service | Size check | Upload validator | N/A | `tests/integration/test_master_regression.py` | Internal | **PASS** |
| Speech-to-Text (STT) | Whisper / Local Fallback | `transcribe` | Transcription | Audio processor | Audio temp | `tests/integration/test_master_regression.py` | External / Offline | **PASS** |
| Unified Learning Brain | Route through `AITutor.ask` | `ask_voice_tutor` | Tutor route | Tutor chat log | Learner Profile | `tests/integration/test_master_regression.py` | Student-facing | **PASS** |
| Text-to-Speech (TTS) | Tone chime / Cloud TTS | `synthesize` | Audio synth | `st.audio` player | WAV artifact | `tests/integration/test_master_regression.py` | External / Offline | **PASS** |
| Audio Session Cleanup | Garbage collection | `cleanup_audio` | File purge | Auto-cleanup | Disk sweep | `tests/integration/test_master_regression.py` | Internal | **PASS** |

---

## 17. Learning Analytics & Observability

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Concept Mastery Metrics | `concept_mastery` dictionary | `get_learning_profile` | Summary stats | Bar chart & cards | Disk JSON | `tests/e2e/test_flows.py` | Student-facing | **PASS** |
| Knowledge Check Counter | `assessment_history` | `get_learning_profile` | History stats | Metric Card | Disk JSON | `tests/pre_manual/test_pre_manual_regressions.py` | Student-facing | **PASS** |
| Strengths & Gaps Breakdown | Dynamic set difference | `get_learning_profile` | Snapshot stats | Dual column list | Disk JSON | `tests/test_integrated_learning_cycle.py` | Student-facing | **PASS** |
| Performance Trend Logging | Historical score list | Profile tracking | Trend stats | Learner Profile | Disk JSON | `tests/integration/test_student_journeys.py` | Student-facing | **PASS** |

---

## 18. Security & Reliability

| Feature | Backend | Facade | API | Streamlit | Persistence | Automated Test | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Prompt Injection Sanitizer | Query normalization | `sanitize_prompt` | Input cleaning | Cleaned input | N/A | `tests/unit/test_core.py` | Student-facing | **PASS** |
| SSRF Defense | `validate_public_url` | URL validator | Scheme checks | Web discovery | Blocklist | `tests/security/test_url_security.py` | Internal | **PASS** |
| Path Traversal Defense | `secure_filename`, safe joins | Path sanitizer | Storage check | File upload | Safe disk | `tests/unit/test_hardening.py` | Internal | **PASS** |
| Upload Payload Protection | 25MB Content-Length guard | Ingestion service | Size middleware | File uploader | Temp buffer | `tests/unit/test_hardening.py` | Internal | **PASS** |
| Secret & Traceback Shield | `ProviderError` / no tracebacks | Exception handler | Controlled JSON | Error banners | Logger mask | `tests/security/test_url_security.py` | Internal | **PASS** |

---

## 19. UI Reachability Summary

| Student Capability | Streamlit Location | Interactive Control | Traced Backend Action | Status |
| :--- | :--- | :--- | :--- | :--- |
| Student Profile & Course | Top Accordion | Text Input & Dropdowns | `ai.sync_learning_context` | **PASS** |
| Chat with AI Tutor | Tutor Tab | `st.chat_input` | `ai.ask_tutor` | **PASS** |
| Tutoring Style Toggle | Tutor Tab | `st.radio` (Direct vs Socratic) | Modulates tutoring guidance | **PASS** |
| Voice Push-to-Talk | Tutor Tab Expander | `st.file_uploader` (WAV/MP3) | `ai.ask_voice_tutor` | **PASS** |
| Course Material Restriction | Tutor Tab Header | `st.multiselect` (Materials) | Constrains retrieval to doc IDs | **PASS** |
| My Learning Mastery Chart | My Learning Tab | `st.bar_chart` | Visualizes `concept_mastery` | **PASS** |
| Next Best Action Card | My Learning Tab | Status Container | `ai.get_next_learning_action` | **PASS** |
| Spaced Repetition Due Queue | My Learning Tab | Remembered / Forgot Buttons | `ai.record_concept_review` | **PASS** |
| Reactive Study Plan | My Learning Tab | Priority Expanders | `ai.get_study_plan` | **PASS** |
| Interactive Diagnostic | My Learning Tab | Form & Radio / Text Questions | `ai.submit_diagnostic` | **PASS** |
| Course Materials Ingestion | Course Materials Tab | `st.file_uploader` (PDF/Word/PPT) | `ai.upload_course_material` | **PASS** |
| Study Tools Generator (15) | Study Tools Tab | Checkboxes (15 types) & Button | `ai.generate_learning_resources`| **PASS** |
| Artifact Viewer & Download | Study Tools Tab | Embedded SVG / DL Buttons | Saves and serves local artifacts| **PASS** |
| Saved Resources History | Study Tools Tab | Historical Accordion | Renders `generated_resources` | **PASS** |
| System Capabilities Status | Footer Expander | Status Overview | `ai.get_supported_capabilities` | **PASS** |
