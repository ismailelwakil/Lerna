"""Security regression tests — identity authority, IDOR, jobs collision,
production config fail-safe, malware-scanner fail-safe.

These encode the security model: the X-Student-Id header identity is
AUTHORITATIVE; body student_id may never override it; every object-level
operation is ownership-authorized.
"""
from __future__ import annotations

import time

import pytest

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from conftest import HEADERS, upload_doc  # noqa: E402


def hdr(student: str) -> dict:
    return {**HEADERS, "X-Student-Id": student}


ALICE, BOB = "alice", "bob"


def _content_count_for(student_id: str) -> int:
    from app.db import get_database
    from app.db.models import ContentItem
    from sqlalchemy import select, func
    db = get_database()
    with db.session_scope() as session:
        return int(session.scalar(
            select(func.count(ContentItem.id)).where(
                ContentItem.student_id == student_id)) or 0)


def _job_count_for(student_id: str) -> int:
    from app.db import get_database
    from app.db.models import GenerationJob
    from sqlalchemy import select, func
    db = get_database()
    with db.session_scope() as session:
        return int(session.scalar(
            select(func.count(GenerationJob.id)).where(
                GenerationJob.student_id == student_id)) or 0)


# ============================================================ identity spoofing
@pytest.mark.parametrize("path,body_extra", [
    ("/api/v1/content/explain", {"topic": "DNS"}),
    ("/api/v1/content/summarize", {"topic": "DNS"}),
    ("/api/v1/content/notes", {"topic": "DNS"}),
    ("/api/v1/content/study-guide", {"topic": "DNS"}),
    ("/api/v1/content/examples", {"topic": "DNS"}),
    ("/api/v1/content/flashcards", {"topic": "DNS"}),
    ("/api/v1/content/quiz", {"topic": "DNS", "num_questions": 3}),
    ("/api/v1/content/exam", {"topic": "DNS", "num_questions": 3}),
    ("/api/v1/content/practice", {"topic": "DNS", "num_questions": 3}),
    ("/api/v1/content/question-bank", {"topic": "DNS", "num_questions": 3}),
    ("/api/v1/content/question-bank/filter", {}),
    ("/api/v1/content/diagram", {"topic": "DNS"}),
    ("/api/v1/content/image", {"topic": "DNS"}),
    ("/api/v1/content/audio", {"topic": "DNS", "text_override": "hi"}),
    ("/api/v1/content/video", {"topic": "DNS", "duration_seconds": 30}),
    ("/api/v1/content/jobs", {"kind": "embeddings", "params": {}}),
])
def test_body_student_id_cannot_spoof_identity(client, path, body_extra):
    """Authenticated=A, body student_id=B → 403 and NOTHING created for B."""
    before = _content_count_for(BOB)
    body = {"student_id": BOB, **body_extra}
    r = client.post(path, headers=hdr(ALICE), json=body)
    assert r.status_code == 403, f"{path}: {r.status_code} {r.text[:120]}"
    assert r.json()["error"]["code"] == "FORBIDDEN"
    # no content persisted under the spoofed identity
    assert _content_count_for(BOB) == before


def test_matching_identity_still_works(client):
    """Authenticated=A + body student_id=A → normal success (back-compat)."""
    r = client.post("/api/v1/content/explain", headers=hdr(ALICE),
                    json={"student_id": ALICE, "topic": "DNS"})
    assert r.status_code == 200
    assert r.json()["meta"]["student_id" if "student_id" in r.json()["meta"]
                         else "content_id"]  # persisted
    assert r.json()["meta"]["content_id"]
    assert _content_count_for(ALICE) >= 1


def test_missing_student_header_rejected_on_generation(client):
    r = client.post("/api/v1/content/explain", headers=HEADERS,
                    json={"student_id": ALICE, "topic": "DNS"})
    assert r.status_code == 422
    assert "X-Student-Id" in r.json()["error"]["message"]


def test_malformed_student_header_rejected(client):
    r = client.post("/api/v1/content/explain",
                    headers={**HEADERS, "X-Student-Id": "bad id with spaces!"},
                    json={"student_id": "bad id with spaces!", "topic": "DNS"})
    assert r.status_code == 422


def test_malformed_body_ids_rejected(client):
    r = client.post("/api/v1/content/explain", headers=hdr(ALICE),
                    json={"student_id": ALICE, "topic": "DNS",
                          "document_ids": ["../../etc/passwd"]})
    assert r.status_code == 422


# ================================================================== verify IDOR
def test_verify_enforces_ownership(client):
    # Alice creates content; Bob tries to verify it
    created = client.post("/api/v1/content/explain", headers=hdr(ALICE),
                          json={"student_id": ALICE, "topic": "DNS"}).json()
    content_id = created["meta"]["content_id"]

    bob_attempt = client.post("/api/v1/content/verify", headers=hdr(BOB),
                              json={"content_id": content_id})
    assert bob_attempt.status_code == 404
    assert "content" not in bob_attempt.json()  # nothing leaked

    alice_attempt = client.post("/api/v1/content/verify", headers=hdr(ALICE),
                                json={"content_id": content_id})
    assert alice_attempt.status_code == 200
    assert alice_attempt.json()["content_id"] == content_id


# ============================================================= jobs regression
def test_jobs_endpoint_no_longer_500s(client):
    """Regression: imported create_job collided with the endpoint name and
    recursed → 500. Must now create and persist a real job."""
    before = _job_count_for(ALICE)
    r = client.post("/api/v1/content/jobs", headers=hdr(ALICE),
                    json={"student_id": ALICE, "kind": "embeddings", "params": {}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["job_id"] and body["status"] in {"QUEUED", "PROCESSING",
                                                 "COMPLETED", "FAILED"}
    assert _job_count_for(ALICE) == before + 1  # persisted under ALICE


def test_jobs_invalid_kind_rejected(client):
    r = client.post("/api/v1/content/jobs", headers=hdr(ALICE),
                    json={"student_id": ALICE, "kind": "rm -rf", "params": {}})
    assert r.status_code == 422


def test_jobs_spoofed_owner_rejected(client):
    r = client.post("/api/v1/content/jobs", headers=hdr(ALICE),
                    json={"student_id": BOB, "kind": "embeddings", "params": {}})
    assert r.status_code == 403
    assert _job_count_for(BOB) == 0


def test_job_status_cross_student_blocked(client):
    job = client.post("/api/v1/content/jobs", headers=hdr(ALICE),
                      json={"student_id": ALICE, "kind": "embeddings",
                            "params": {}}).json()
    assert client.get(f"/api/v1/content/jobs/{job['job_id']}",
                      headers=hdr(BOB)).status_code == 404
    assert client.get(f"/api/v1/content/jobs/{job['job_id']}/status",
                      headers=hdr(BOB)).status_code == 404
    assert client.get(f"/api/v1/content/jobs/{job['job_id']}",
                      headers=hdr(ALICE)).status_code == 200


# ==================================================== cross-student (documents)
def test_from_document_cross_student_blocked(client):
    victim_doc = upload_doc(client, "victim-user")
    r = client.post("/api/v1/content/from-document", headers=hdr(ALICE),
                    json={"student_id": ALICE, "document_ids": [victim_doc],
                          "instruction": "Summarize this"})
    assert r.status_code == 404


def test_generation_with_foreign_document_ids_blocked(client):
    victim_doc = upload_doc(client, "victim-user")
    for path in ("/api/v1/content/explain", "/api/v1/content/quiz"):
        r = client.post(path, headers=hdr(ALICE),
                        json={"student_id": ALICE, "topic": "DNS",
                              "document_ids": [victim_doc],
                              **({"num_questions": 3} if "quiz" in path else {})})
        assert r.status_code == 404, path


def test_question_bank_filter_cross_student_blocked(client):
    """Bob's filter endpoint can never return Alice's stored questions."""
    # seed a question set for Alice directly (quiz generation needs a live
    # structured provider, unavailable in mock mode)
    from app.db import get_database
    from app.db.models import Question, QuestionSet
    from app.core.security import new_id
    db = get_database()
    set_id = new_id()
    question_id = new_id()
    with db.session_scope() as session:
        session.add(QuestionSet(id=set_id, student_id=ALICE, kind="quiz",
                                topic="DNS", meta={}))
        session.add(Question(id=question_id, set_id=set_id, index=0, type="MCQ",
                             prompt="What does DNS resolve?",
                             options=["A", "B", "C", "D"], correct_answer="0",
                             explanation="", difficulty="easy"))
    # Alice sees her question
    mine = client.post("/api/v1/content/question-bank/filter", headers=hdr(ALICE),
                       json={"student_id": ALICE, "randomize": False})
    assert mine.status_code == 200
    assert any(q["question_id"] == question_id
               for q in mine.json().get("questions", []))
    # Bob must not see it
    theirs = client.post("/api/v1/content/question-bank/filter", headers=hdr(BOB),
                         json={"student_id": BOB, "randomize": False})
    assert theirs.status_code in {200, 404}
    if theirs.status_code == 200:
        assert not any(q["question_id"] == question_id
                       for q in theirs.json().get("questions", []))
    # Bob cannot ask the filter to run AS Alice
    spoof = client.post("/api/v1/content/question-bank/filter", headers=hdr(BOB),
                        json={"student_id": ALICE, "randomize": False})
    assert spoof.status_code == 403


# ================================================= production config fail-safe
def test_production_refuses_to_start_without_api_key():
    from app.core.config import reset_settings
    from app.main import validate_production_config

    settings = reset_settings()
    settings.is_prod = True
    settings.api_key_explicit = False
    with pytest.raises(RuntimeError, match="CONTENT_API_KEY"):
        validate_production_config(settings)
    # explicit key → passes (scanner set: production requires a real scanner)
    settings.api_key_explicit = True
    settings.malware_scanner = "clamav"
    validate_production_config(settings)
    # dev without key → allowed (documented open dev mode)
    settings.is_prod = False
    settings.api_key_explicit = False
    validate_production_config(settings)
    reset_settings()


# ============================================== malware scanning fail-safe
def test_required_scanner_missing_fails_safely(client):
    from app.core.config import get_settings
    settings = get_settings()
    original_required, original_scanner = (settings.require_malware_scanning,
                                           settings.malware_scanner)
    settings.require_malware_scanning = True
    settings.malware_scanner = "none"  # required but nothing configured
    try:
        doc = upload_doc(client, "scan-user")
        r = client.post(f"/api/v1/content/documents/{doc}/process",
                        headers=hdr("scan-user"), json={})
        job_id = r.json()["job_id"]
        for _ in range(40):
            state = client.get(f"/api/v1/content/jobs/{job_id}",
                               headers=hdr("scan-user")).json()
            if state["status"] in {"COMPLETED", "FAILED"}:
                break
            time.sleep(0.15)
        assert state["status"] == "FAILED"
        assert "no scanner is configured" in state["error"]
        # the document is NOT marked processed/clean
        doc_state = client.get(f"/api/v1/content/documents/{doc}",
                               headers=hdr("scan-user")).json()
        assert doc_state["status"] == "failed"
    finally:
        settings.require_malware_scanning = original_required
        settings.malware_scanner = original_scanner