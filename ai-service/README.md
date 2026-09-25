# AI Academic Adaptive Learning System

A production-oriented adaptive learning feature for a larger university platform. The runtime implements two distinct tutoring policies: source-constrained answers from student/course files, and general academic answers grounded in dynamically discovered trusted external sources. The LLM synthesizes evidence; it is not used as the factual source of truth when trusted evidence is unavailable.

## Core learning loop

Student query/upload → language detection → English normalization → source policy → trusted evidence → personalized tutor → diagnostic assessment → concept diagnosis → persistent learner profile → next best action → personalized content generation → reassessment → mastery update.

## Windows 11 / PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python -m pytest -q
python scripts\smoke_test.py
python -m streamlit run app\streamlit_app.py
```

## API keys and what they enable

`TAVILY_API_KEY` enables real trusted external search. For the intended general-question flow, set `ENABLE_WEB_SEARCH=true` and provide this key. If it is missing, the runtime does not silently answer from LLM memory; it returns a controlled trusted-search-unavailable response.

LLM keys are optional individually. Configure one or more of `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GROQ_API_KEY`. The router only treats providers with configured credentials as real active providers. If one provider is configured, multi-provider mode is false. If two or more are configured, tasks can be routed by capability and language fit.

`AI_PROVIDER=auto` is recommended when multiple keys are present. `AI_MODEL` can override the preferred provider's model. Keep provider model names current for your account before live demo.

## Source policy

When a student selects uploaded material or explicitly says to answer from it, only that material is used. Missing evidence causes hard abstention. General academic questions use trusted discovery first: source planning → real search → trust validation → safe fetch → cleaning → chunking → embedding/indexing → hybrid retrieval → grounded answer with citations.

## Multilingual policy

The architecture supports English, Arabic, French, Swahili, Hausa, Amharic, Somali, Yoruba, Igbo, and Zulu. The original query is preserved. Non-English input is normalized to English for academic processing, and the final grounded answer is translated back while preserving technical terms, citations, URLs, code, equations, filenames, and identifiers.

## Content creation

Supported runtime resource types are explanation, summary, notes, flashcards, quiz, code, SVG diagram, and PPTX presentation. Image/audio/video are reported unavailable unless a real multimedia provider is added; fake artifacts are never generated. Content generation consumes the same learner profile and trusted knowledge layer as the Tutor.

## Assessment

Diagnostics support MCQ, short-answer, true/false, and code-style questions. Objective questions include a localized `I don't know` option. Free-text questions expose an `I don't know / skip` UI choice. This is treated as missing knowledge evidence, not automatically as a misconception.

See `ARCHITECTURE.md`, `INTEGRATION.md`, and `TEST_REPORT.md` for implementation and verification details.