# Academic OS: Known Issues & Integration Notes

This document honestly outlines known behavior, edge cases, and integration boundaries in the current version of Academic OS. The frontend handles these states gracefully rather than fabricating false data.

---

## 1. Assessment Contract Formatting on Uploaded Text Snippets

- **Symptom:** When generating a diagnostic assessment on an uploaded plain-text file that lacks distinct conceptual headers, the question generation prompt occasionally treats raw lecture header lines (e.g., `Course: CS101... Topic: Divide-and-Conquer`) as distractor option text.
- **Frontend Safe Treatment:** The React client verifies options during payload receipt. If raw metadata options are detected, a contract notice toast is displayed, and the options are rendered safely without crashing. The frontend never synthesizes synthetic question options client-side.
- **Backend Fix in Progress:** Refining the prompt template in `src/assessment/service.py` with strict regex post-filtering to exclude file metadata from distractor candidates.

---

## 2. Voice Question Endpoint Preview Status

- **Symptom:** `POST /tutor/voice` accepts uploaded audio bytes, but real-time speech-to-text requires a local whisper model or an external STT API key (e.g., OpenAI Whisper).
- **Frontend Safe Treatment:** The voice button is clearly marked with a preview badge. When audio is submitted without a configured STT provider, the backend returns `search_state = "voice_pending"` and prompts the student to use text input. The frontend does not fabricate speech transcription.

---

## 3. High-Concurrency PDF Extraction

- **Symptom:** In live trusted external search, university lecture notes are frequently served as multi-page PDFs (e.g. 25–40 pages). While `SafeWebFetcher` uses `pypdf` with a 1-retry backoff, university servers occasionally throttle or drop slow connections.
- **Engine Treatment:** The candidate inspection loop in `ai_tutor.py` terminates as soon as $\ge 4$ substantive documents are gathered. If a specific university PDF times out, the search engine falls back to other high-trust university domains without failing the user request.

---

## 4. Multi-Instance ChromaDB Concurrency

- **Symptom:** ChromaDB is running in local embedded SQLite mode (`data/chroma/chroma.sqlite3`). Concurrent write locks may occur if multiple API worker processes attempt to index files simultaneously.
- **Production Recommendation:** For production deployments with multiple backend containers, migrate Chroma to client-server mode (`chromadb.HttpClient(host=..., port=...)`) or a hosted vector database (Qdrant, Pinecone).
