# Integration Guide

The stable facade is `src.integration.service.LearningIntelligenceModule`.

Public methods:

- `sync_learning_context(...)`
- `ask_tutor(...)`
- `upload_course_material(...)`
- `list_course_materials(...)`
- `create_diagnostic(...)`
- `submit_diagnostic(...)`
- `get_learning_profile(...)`
- `get_content_creation_context(...)`
- `get_next_learning_action(...)`
- `generate_learning_resources(...)`
- `get_supported_capabilities()`
- `health()`

The host app should pass authenticated student/course/session context. It must not depend on Chroma, SentenceTransformer, Tavily, or any LLM SDK directly.

For uploaded-material mode, pass selected `document_ids` to `ask_tutor`, or allow the student's wording to trigger source-constrained behavior. For general academic mode, pass no document IDs; the Tutor invokes trusted external discovery rather than using uploaded files as a fallback.

The Content Creation runtime uses the same learner profile and evidence policy. The historical Content Creation codebase is retained under `source_modules/content_creation_original/` for audit/traceability, but its independent Qdrant/RAG path is not activated in the integrated runtime because that would create two competing knowledge layers.