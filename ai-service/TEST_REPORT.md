# Test Report

## Integrated runtime

- Automated deterministic tests: 43 passed, 0 failed, 0 skipped.
- Smoke test: PASS.
- Python compile check (`compileall`): PASS.

Coverage added/retained includes uploaded-file ingestion/retrieval, hard source-constrained abstention, trusted-external general question flow with deterministic trusted-search fixture, Arabic normalization/round-trip architecture, profile persistence, assessment/profile updates, pooling contradiction regression, I-don't-know handling, personalization, content-context adaptation, truthful provider status, URL security, Chroma adapter behavior, and facade/e2e flows.

## Original Content Creation audit suite

- 96 passed, 0 failed, 3 skipped.
- The original module is retained for traceability but its duplicate RAG is not the active integrated knowledge runtime.

## Combined deterministic/audit execution

- Passed: 139
- Failed: 0
- Skipped: 3

## Real external provider/search tests

No external API credentials were available in the packaging environment. Therefore:

- Tavily live trusted search: NOT EXECUTED; provider-dependent.
- Gemini live call: NOT EXECUTED; provider-dependent.
- OpenAI live call: NOT EXECUTED; provider-dependent.
- Anthropic live call: NOT EXECUTED; provider-dependent.
- Groq live call: NOT EXECUTED; provider-dependent.
- Real multi-provider routing E2E: SKIPPED because fewer than two real configured providers were available.

The code does not report those tests as passed. Configure keys in `.env` and run provider/search smoke tests locally before claiming live-provider success in the hackathon demo.

## Streamlit

`app/streamlit_app.py` passes Python compilation. A live Streamlit server could not be started in the packaging container because Streamlit is not installed in that container. `streamlit` is present in `requirements.txt`; after installing requirements in the target environment, run the documented command and execute the manual UI acceptance checklist.

UI hardening included: larger top padding to avoid clipped header, disabled file watcher config, source-mode guidance, cleaned `svg`/heading artifacts, source badges, localized I-don't-know assessment controls, light/dark styles, student-facing error wording, and no provider/vector debug data in normal UI.

## Implemented and tested

Uploaded-material RAG; source-constrained hard abstention; deterministic trusted external discovery path; trusted-source ingestion/indexing; hybrid retrieval; citation provenance; learner profile persistence; assessment contradiction regression; I-don't-know semantics; personalization/next action; shared content context; truth-preserving provider registry/routing state; SVG/PPTX real artifact creation architecture; URL/SSRF guard primitives.

## Implemented but provider-dependent

Live trusted web discovery/fetch through Tavily; live multilingual translation through configured LLM; live Gemini/OpenAI/Anthropic/Groq generation; real cross-provider content routing.

## Not available without an added real provider

Image generation, audio generation, and video generation. The runtime reports these as unavailable instead of creating fake artifacts.