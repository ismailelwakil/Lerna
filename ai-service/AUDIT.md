# Implementation Audit

## Existing integrated Tutor/Learner code

Reusable: persistent profile store, SentenceTransformer/Chroma adapters, upload validation/extraction, hybrid semantic+lexical retrieval, learner profile, assessment regression logic, personalization, Next Best Action, facade, Streamlit shell, SVG/PPTX artifact creation.

Critical gaps fixed in this rebuild: general questions previously retrieved local material and then abstained instead of running trusted discovery; trusted search existed but was not wired into Tutor orchestration; external search snippets were not processed through the same ingestion/index; multilingual detection did not perform the required English normalization/return translation; `I don't know` was not an explicit diagnostic state; provider status did not explicitly state single vs multi-provider execution; Streamlit retained clipped-header/SVG rendering issues.

## Original Content Creation module

The original codebase is broad and has real architecture for text/media/provider/storage/vector abstractions, intent routing, assessment generation, verification, and security. Its own tests pass (96 passed, 3 skipped in this packaging run). It also maintains an independent Qdrant/in-memory RAG path and provider/fallback stack. Activating that RAG beside the Tutor's Chroma pipeline would violate the single shared knowledge-layer requirement, so the original module is retained under `source_modules/content_creation_original/` for audit/traceability while the integrated runtime uses one shared ingestion/retrieval layer.

The integrated content path reuses learner context, trusted evidence, capability routing, and real SVG/PPTX artifacts. Unsupported image/audio/video are reported unavailable rather than faked. Future media-provider integration should connect through the same shared knowledge policy rather than restoring a second RAG.

## Truthfulness rule

Provider adapters, search adapters, and test doubles are distinguished. Mock tests prove deterministic orchestration, not live API availability. Live provider/search success is only reportable after credentials are configured and the provider-dependent smoke scripts pass.