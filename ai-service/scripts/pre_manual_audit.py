from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path

from src.orchestration.factory import build_system
from src.contracts.models import StudentQuery, Chunk, Evidence
from src.integration.service import build_module
from src.voice.service import VoiceTutorService, VoiceError
from infrastructure.search.trusted import is_wikipedia, trust, source_tier

def audit():
    temp_dir = tempfile.mkdtemp(prefix="academic_os_audit_")
    print(f"Running automated feature audit in {temp_dir}...")
    ai = build_system(temp_dir, test_mode=True)
    mod = build_module(temp_dir, test_mode=True)

    # 1. Cold Start
    print("Testing Cold Start...")
    p_cold = ai.create_or_load_student("cold-student", "Cold User", "Physics", "en")
    assert len(p_cold.concept_mastery) == 0
    assert len(p_cold.misconceptions) == 0
    assert len(p_cold.weak_concepts) == 0
    nba_cold = ai.learning_orchestrator.next_action(p_cold)
    assert nba_cold.action == "progress"

    # 2. Material RAG with Synthetic Fact
    print("Testing Material RAG with Synthetic Fact...")
    f_path = Path(temp_dir) / "synth_course.txt"
    f_path.write_text(
        "Quantum Computing Module 1:\n"
        "Qubits can exist in superposition. "
        "SyntheticFactXYZ99: The specific coherence duration of CryoProcessor-Omega is exactly 417 microseconds.\n",
        encoding="utf-8"
    )
    meta = ai.upload_document("cold-student", f_path, "synth_course.txt", course="Physics")
    resp_synth = ai.ask(StudentQuery(
        student_id="cold-student",
        session_id="s1",
        text="What is the exact coherence duration of CryoProcessor-Omega according to the lecture?",
        course="Physics",
        document_ids=[meta.document_id]
    ))
    assert not resp_synth.abstained
    assert "417" in resp_synth.answer
    assert resp_synth.knowledge_source == "uploaded_material"

    # 3. Trusted General Noisy Retrieval & Wikipedia
    print("Testing Trusted General Noisy Retrieval...")
    resp_bg = ai.ask(StudentQuery(
        student_id="cold-student",
        session_id="s2",
        text="What is binary search? Explain how it works, state its time complexity, and mention the main requirement that must be satisfied before using it.",
        course="Physics"
    ))
    assert not resp_bg.abstained
    assert "o(log n)" in resp_bg.answer.lower()
    assert "treap" not in resp_bg.answer.lower()
    assert "heap sort" not in resp_bg.answer.lower()

    # 4. Content Generation: All 14 Types
    print("Testing All 14 Content Types...")
    all_14 = [
        "explanation", "summary", "notes", "study_guide", "flashcards",
        "quiz", "exam", "practice", "code", "coding_exercise",
        "diagram", "presentation", "analogy", "comparison", "question_bank"
    ]
    outputs, _ = ai.generate_content("cold-student", "Binary Search", all_14, "en")
    for k in all_14:
        assert k in outputs, f"Missing content type: {k}"
        assert outputs[k]["type"] in ("text", "file")

    # 5. Voice Boundary
    print("Testing Voice Boundaries...")
    voice = VoiceTutorService(ai, audio_dir=os.path.join(temp_dir, "audio"))
    # Oversized audio
    try:
        voice._validate_audio(b"RIFF" + b"\x00" * (11 * 1024 * 1024))
        print("FAIL: Oversized audio not rejected")
    except VoiceError:
        pass
    # Corrupt audio
    try:
        voice._validate_audio(b"CORRUPT_BYTES_XYZ")
        print("FAIL: Corrupt audio not rejected")
    except VoiceError:
        pass

    # 6. Cross-Student Isolation
    print("Testing Cross-Student Isolation...")
    p_b = ai.create_or_load_student("student-b", "Student B", "History", "en")
    docs_b = ai.ingestion.list_documents("student-b")
    assert len(docs_b) == 0

    # 7. Security SSRF
    print("Testing Security SSRF...")
    from infrastructure.search.trusted import validate_public_url
    assert validate_public_url("http://127.0.0.1:8000") is False
    assert validate_public_url("http://169.254.169.254/latest/meta-data/") is False
    assert validate_public_url("file:///etc/passwd") is False

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("ALL AUDIT SCENARIOS PASSED!")

if __name__ == "__main__":
    audit()
