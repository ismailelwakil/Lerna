from __future__ import annotations

import os
from pathlib import Path
import pytest

from src.orchestration.factory import build_system
from src.contracts.models import StudentQuery, Evidence
from src.integration.service import build_module


def test_pm_b01_evidence_is_wikipedia_attribute(tmp_path):
    """PM-B01: Evidence model must have is_wikipedia attribute populated correctly."""
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-wiki", "Test", "Computer Science", "en")

    # Retrieve evidence from knowledge base
    ev_list, _ = ai.retrieval.retrieve("binary search", "s-wiki", None)
    for ev in ev_list:
        assert hasattr(ev, "is_wikipedia"), "Evidence must have is_wikipedia attribute"
        assert isinstance(ev.is_wikipedia, bool)


def test_pm_b02_multilingual_arabic_localized_body(tmp_path):
    """PM-B02: Arabic queries must produce localized Arabic body keywords in offline/mock mode."""
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-ar", "Omar", "Algorithms", "ar")

    resp = ai.ask(StudentQuery(
        student_id="s-ar",
        session_id="s-ar-1",
        text="اشرحلي ازاي بيشتغل البحث الثنائي binary search وايه التعقيد بتاعه",
        course="Algorithms",
        preferred_language="ar",
    ))
    assert not resp.abstained
    assert resp.answer.startswith("شرح مخصص:")
    assert any(term in resp.answer for term in ["البحث", "الثنائي", "مصفوفة", "مرتبة", "نصف"])


def test_pm_b03_saved_resources_persistence_and_retrieval(tmp_path):
    """PM-B03: Generated study resources must persist in profile.generated_resources and be listable."""
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-res", "ResUser", "Algorithms", "en")

    # Generate notes and quiz
    out, _ = ai.generate_content("s-res", "Binary Search", ["notes", "quiz"], "en")
    p = ai.get_student_profile("s-res")
    assert len(p.generated_resources) >= 1
    last_res = p.generated_resources[-1]
    assert last_res["topic"] == "Binary Search"
    assert "notes" in last_res["outputs"]
    assert "quiz" in last_res["outputs"]


def test_pm_b04_system_capabilities_honesty(tmp_path):
    """PM-B04: System capabilities must truthfully report all declared types and false for unsupported features."""
    ai = build_system(str(tmp_path), test_mode=True)
    caps = ai.supported_capabilities()

    assert len(caps["content_types"]) >= 14
    for expected_type in [
        "explanation", "summary", "notes", "study_guide", "flashcards",
        "quiz", "exam", "practice", "code", "coding_exercise",
        "diagram", "presentation", "analogy", "comparison", "question_bank",
    ]:
        assert expected_type in caps["content_types"]

    assert caps["ocr"] is False
    assert caps["realtime_voice"] is False


def test_pm_b05_dynamic_preferences_sync(tmp_path):
    """PM-B05: Syncing student preferences updates the active course, language, and learning style."""
    mod = build_module(str(tmp_path), test_mode=True)
    p1 = mod.sync_learning_context("s-pref", "Sam", "Intro CS", "en", "step-by-step")
    assert p1.student.course == "Intro CS"

    # Update preferences
    p2 = mod.sync_learning_context("s-pref", "Sam", "Advanced AI", "ar", "socratic")
    assert p2.student.course == "Advanced AI"
    assert p2.student.preferred_language == "ar"
    assert p2.student.learning_preference == "socratic"


def test_pm_b06_binary_search_mock_query_coverage(tmp_path):
    """PM-B06: Varied phrasings of binary search questions must receive full pedagogical answers."""
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-bs", "BSUser", "Algorithms", "en")

    queries = [
        "What is binary search and what is its time complexity?",
        "Binary search details and runtime",
        "Can you explain binary search to me?",
    ]
    for q_text in queries:
        resp = ai.ask(StudentQuery(student_id="s-bs", session_id="s-bs", text=q_text, course="Algorithms"))
        assert not resp.abstained
        assert "binary search" in resp.answer.lower()
        assert "o(log n)" in resp.answer.lower()
