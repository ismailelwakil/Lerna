#!/usr/bin/env python3
"""Example integration client — how the MAIN EDUnation backend calls this module.

Run the module first:   uvicorn app.main:app --port 8001
Then:                   python examples/integration_client.py

Copy these call patterns into the main platform's backend (proxy them through
your own API — never expose this module or its key to browsers).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
API_KEY = "REPLACE_WITH_CONTENT_API_KEY_FROM_ENV"     # server-side secret only
STUDENT = "student-123"

H = {"X-API-Key": API_KEY, "X-Student-Id": STUDENT, "Content-Type": "application/json"}


def call(method: str, path: str, body: dict | None = None, headers: dict | None = None):
    req = urllib.request.Request(BASE + path, method=method)
    for key, value in {**H, **(headers or {})}.items():
        req.add_header(key, value)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def demo() -> None:
    print("1) health / provider readiness")
    status, health = call("GET", "/health")
    print("  ", status, health["llm_mode"], health["providers"])

    print("\n2) upload a document (multipart) + process it (async job)")
    boundary = "----eduBoundary7MA4YWxkTrZu0gW"
    text = ("Lecture: Subnetting. A /26 prefix leaves 6 host bits → 64 addresses, "
            "62 usable. The magic number is 256-192=64, so subnets start at .0, .64, .128, .192.")
    payload = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
               f"filename=\"lecture.txt\"\r\nContent-Type: text/plain\r\n\r\n{text}\r\n"
               f"--{boundary}--\r\n").encode()
    req = urllib.request.Request(
        BASE + "/api/v1/content/documents/upload", method="POST", data=payload)
    req.add_header("X-API-Key", API_KEY)
    req.add_header("X-Student-Id", STUDENT)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req) as resp:
        doc = json.loads(resp.read())["document_id"]
    print("   document_id:", doc)

    _, job = call("POST", f"/api/v1/content/documents/{doc}/process", {})
    for _ in range(40):
        _, state = call("GET", f"/api/v1/content/jobs/{job['job_id']}")
        if state["status"] in {"COMPLETED", "FAILED"}:
            break
        time.sleep(0.4)
    print("   processing:", state["status"], state.get("result", {}).get("chunks"), "chunks")

    print("\n3) grounded generation from the material")
    status, result = call("POST", "/api/v1/content/explain", {
        "student_id": STUDENT, "topic": "subnetting a /26",
        "document_ids": [doc], "level": "beginner",
        "learner": {"knowledge_gaps": ["binary math"]}})
    print("  ", status, "| grounded:", result.get("meta", {}).get("grounded"),
          "| verified:", result.get("meta", {}).get("verified"))

    print("\n4) natural-language from-document: 'Create 10 MCQs'")
    status, quiz = call("POST", "/api/v1/content/from-document", {
        "student_id": STUDENT, "document_ids": [doc],
        "instruction": "Create 10 MCQs from this material"})
    print("  ", status, "| total:", quiz.get("total"), "| first:",
          (quiz.get("questions") or [{}])[0].get("question", "")[:60])

    print("\n5) study guide + audio of it (voice lesson)")
    status, guide = call("POST", "/api/v1/content/study-guide", {
        "student_id": STUDENT, "topic": "subnetting", "document_ids": [doc]})
    print("  ", status, "guide content_id:", guide.get("meta", {}).get("content_id", "")[:8])
    status, audio = call("POST", "/api/v1/content/audio", {
        "student_id": STUDENT, "topic": "subnetting",
        "text_override": "A slash twenty-six network has sixty-four addresses. "
                         "Sixty-two are usable for hosts."})
    print("  ", status, "audio:", audio.get("mime", audio.get("error", {}).get("code")))

    print("\nFull contract details: INTEGRATION.md · interactive docs: /api/v1/docs")


if __name__ == "__main__":
    demo()