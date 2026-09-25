# START HERE — integrating this module 🚀

This is the **EDUnation Content Creation Module** — a standalone service the
main EDUnation platform calls over HTTP. Read `INTEGRATION.md` for the full
contract; this page gets you running in 2 minutes.

## 1. Run it

```bash
cd content_creation
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # add keys (module also runs fully in offline mock mode)
uvicorn app.main:app --port 8001
```

Check: http://localhost:8001/health  → provider readiness snapshot.
Interactive docs: http://localhost:8001/api/v1/docs

## 2. The ONE thing to know

Every call carries two headers — that's the whole auth model:

```
X-API-Key:    <CONTENT_API_KEY from .env>     ← server-to-server secret
X-Student-Id: <your platform's user id>       ← opaque string, you own it
```

Call this module ONLY from your backend (proxy pattern) — never from a browser.

## 3. Try the example integration client

```bash
python examples/integration_client.py http://localhost:8001
```

It demonstrates the full loop: upload → process → grounded explain →
"Create 10 MCQs" → study guide → voice audio.

## 4. Fastest integration path into main EDUnation

In the main backend, add a small proxy service (pseudo-code):

```python
# edunation backend (FastAPI) — app/services/content_client.py
CONTENT_BASE = "http://localhost:8001/api/v1/content"

async def create_quiz(user, goal_text, document_ids):
    return await httpx.post(f"{CONTENT_BASE}/quiz", headers={
        "X-API-Key": settings.CONTENT_API_KEY,
        "X-Student-Id": user.id,
    }, json={"student_id": user.id, "topic": goal_text,
             "document_ids": document_ids, "num_questions": 5})
```

Then wire tutor intents ("make me a quiz", "summarize this file",
"read this to me") to these calls. All response shapes are in
`INTEGRATION.md` §4.

## 5. Tests (offline, no keys needed)

```bash
python -m pytest tests -q        # 42 tests
```

## 6. Docs map

- `README.md` — architecture, env vars, API list, deployment
- `INTEGRATION.md` — full API contract, learner-context format, error codes
- `SECURITY.md` — security controls + red-team results + limits