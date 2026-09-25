"""Test configuration — offline, mocked providers, no real keys required."""
from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="cc_test_")
os.environ["CONTENT_LLM_MODE"] = "mock"
os.environ["CONTENT_API_KEY"] = "test-key"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["ASSET_SIGNING_SECRET"] = "test-signing-secret"
os.environ["QDRANT_URL"] = ""          # memory vector store
os.environ["QDRANT_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""      # local-hash embeddings
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["ELEVENLABS_API_KEY"] = ""
os.environ["DEEPGRAM_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["GROQ_API_KEY"] = ""
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""
os.environ["RATE_LIMITS"] = '{"default":"60/60","generate":"20/60","upload":"12/60","jobs":"10/60","expensive":"200/3600"}'

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

HEADERS = {"X-API-Key": "test-key"}


@pytest.fixture(scope="session")
def client():
    from app.main import create_app
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture()
def student(client):
    sid = "stu-test-1"
    return sid, {**HEADERS, "X-Student-Id": sid}


def upload_doc(client, student_id, name="notes.txt", content=b"DNS translates "
              b"names into IPs. A records map to IPv4. TTL controls caching."):
    r = client.post("/api/v1/content/documents/upload",
                    headers={**HEADERS, "X-Student-Id": student_id},
                    files={"file": (name, content, "text/plain")})
    assert r.status_code == 200, r.text
    return r.json()["document_id"]


def process_doc(client, student_id, doc_id) -> dict:
    r = client.post(f"/api/v1/content/documents/{doc_id}/process",
                    headers={**HEADERS, "X-Student-Id": student_id}, json={})
    assert r.status_code == 200
    import time
    for _ in range(40):
        st = client.get(f"/api/v1/content/jobs/{r.json()['job_id']}",
                        headers={**HEADERS, "X-Student-Id": student_id}).json()
        if st["status"] in {"COMPLETED", "FAILED"}:
            return st
        time.sleep(0.15)
    raise AssertionError("job did not finish")