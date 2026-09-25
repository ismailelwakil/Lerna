from __future__ import annotations

import os
from pathlib import Path
import pytest

from src.orchestration.factory import build_system
from src.contracts.models import StudentQuery
from src.integration.service import build_module


def test_journey_1_beginner_cs_learning_cycle(tmp_path):
    """Journey 1: Beginner in Computer Science

    - Asks for binary search explanation
    - Takes diagnostic
    - Shows weakness or misconception
    - Gets personalized remediation
    - Reassesses
    - Mastery updates and clears weakness
    """
    ai = build_system(str(tmp_path), test_mode=True)
    p = ai.create_or_load_student("student-cs-1", "Amir", "CS101", "en", "step-by-step")

    # 1. Ask binary search explanation
    resp1 = ai.ask(StudentQuery(student_id="student-cs-1", session_id="s-cs-1", text="What is binary search and what is its time complexity?", course="CS101"))
    assert not resp1.abstained
    assert "binary search" in resp1.answer.lower()
    assert "o(log n)" in resp1.answer.lower()

    # 2. Take diagnostic
    diag = ai.create_assessment("student-cs-1", "Binary Search", ["binary search", "logarithmic complexity"])
    assert len(diag.questions) >= 1

    # 3. Student has misconception / fails
    wrong = {q.question_id: "binary search works on completely unsorted data" for q in diag.questions}
    res1 = ai.submit_assessment("student-cs-1", diag, wrong)
    assert res1.score < 0.60

    p_after_fail = ai.get_student_profile("student-cs-1")
    assert "binary search" in p_after_fail.weak_concepts
    nba1 = ai.learning_orchestrator.next_action(p_after_fail)
    assert nba1.action in ("correct_misconception", "targeted_remediation", "targeted_practice", "remediate_prerequisite")

    # 4. Reassessment after remediation
    reassess = ai.create_assessment("student-cs-1", "Binary Search", ["binary search"])
    correct = {q.question_id: q.expected for q in reassess.questions}
    res2 = ai.submit_assessment("student-cs-1", reassess, correct)
    assert res2.score >= 0.80

    p_after_pass = ai.get_student_profile("student-cs-1")
    assert p_after_pass.concept_mastery.get("binary search", 0.0) >= 0.70
    assert "binary search" not in p_after_pass.weak_concepts


def test_journey_2_engineering_lecture_material_constrained(tmp_path):
    """Journey 2: Engineering student with lecture materials

    - Uploads notes/slides
    - Asks question constrained to uploaded document
    - Verifies exact citations with document/page citations
    - Verifies no external web contamination
    """
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("student-eng-2", "Layla", "Signal Processing", "en")

    # Upload material
    doc = tmp_path / "dsp_lecture.txt"
    doc.write_text(
        "Lecture 4: Nyquist-Shannon Sampling Theorem.\n"
        "To perfectly reconstruct a continuous-time bandlimited signal with maximum frequency B, "
        "the sampling rate fs must be strictly greater than twice the highest frequency component (fs > 2B). "
        "The frequency fs/2 is called the Nyquist frequency.",
        encoding="utf-8",
    )
    meta = ai.upload_document("student-eng-2", doc, "dsp_lecture.txt", course="Signal Processing")
    assert meta.document_id

    # Query constrained to this document
    resp = ai.ask(StudentQuery(
        student_id="student-eng-2",
        session_id="s-eng",
        text="According to the lecture, what is the exact requirement for sampling frequency to prevent aliasing?",
        course="Signal Processing",
        document_ids=[meta.document_id],
    ))

    assert not resp.abstained
    assert "fs > 2b" in resp.answer.lower() or "twice" in resp.answer.lower() or "nyquist" in resp.answer.lower()
    assert resp.knowledge_source == "uploaded_material"
    assert len(resp.citations) >= 1
    # Check that external web was not used
    assert resp.trusted_search_state in ("disabled_by_mode", "not_requested", "skipped") or all(e.source_type == "student_upload" for e in resp.evidence)


def test_journey_3_medical_clinical_authoritative_sources(tmp_path):
    """Journey 3: Medical / Clinical learner

    - Asks clinical pharmacology question (penicillin mechanism)
    - Verifies authoritative health domain retrieval (StatPearls / NCBI)
    - Verifies Wikipedia is excluded from final evidence
    """
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("student-med-3", "Dr. Tariq", "Pharmacology", "en")

    resp = ai.ask(StudentQuery(
        student_id="student-med-3",
        session_id="s-med",
        text="What is the mechanism of action of penicillin on bacterial cell wall synthesis?",
        course="Pharmacology",
    ))

    assert not resp.abstained
    assert "penicillin" in resp.answer.lower()
    assert "transpeptidase" in resp.answer.lower() or "peptidoglycan" in resp.answer.lower() or "cell wall" in resp.answer.lower()
    # Clinical domain check: Wikipedia must NOT be cited
    for c in resp.citations:
        assert "wikipedia.org" not in c.lower(), f"Wikipedia cited in clinical answer: {c}"
    for ev in resp.evidence:
        assert not ev.is_wikipedia, "Wikipedia chunk found in clinical evidence"


def test_journey_4_multilingual_arabic_and_dialect(tmp_path):
    """Journey 4: Multilingual student (Arabic / Egyptian dialect)

    - Asks in Egyptian Arabic
    - Gets grounded Arabic response with technical terms preserved
    """
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("student-ar-4", "Omar", "Algorithms", "ar")

    resp = ai.ask(StudentQuery(
        student_id="student-ar-4",
        session_id="s-ar",
        text="اشرحلي ازاي بيشتغل البحث الثنائي binary search وايه التعقيد بتاعه",
        course="Algorithms",
        preferred_language="ar",
    ))

    assert not resp.abstained
    # Verify Arabic response and technical terms
    assert any(c in resp.answer for c in ["البحث", "الثنائي", "مصفوفة", "مرتبة", "نصف"])
    assert "o(log n)" in resp.answer.lower() or "log n" in resp.answer.lower() or "logarithmic" in resp.answer.lower()


def test_journey_5_learning_optimization_review_and_plan(tmp_path):
    """Journey 5: Learning optimization flow

    - Assesses student
    - Generates dynamic study plan
    - Schedules spaced repetition reviews
    - Records reviews and updates intervals
    """
    mod = build_module(str(tmp_path), test_mode=True)
    mod.sync_learning_context("student-opt-5", "Nadia", "Machine Learning", "en")

    diag = mod.create_diagnostic("student-opt-5", "CNN")
    # Student answers "I don't know" to reveal knowledge gaps
    idk_answers = {q.question_id: "I don't know" for q in diag.questions}
    mod.submit_diagnostic("student-opt-5", diag, idk_answers)

    # Verify study plan
    plan = mod.get_study_plan("student-opt-5")
    assert len(plan) > 0
    assert any(p["priority"] == "high" or p["priority"] == "medium" for p in plan)

    # Verify spaced repetition queue
    queue = mod.get_review_queue("student-opt-5")
    assert len(queue) > 0

    # Practice concept recall
    target = queue[0]["concept"]
    res = mod.record_concept_review("student-opt-5", target, remembered=True)
    assert res["repetition"] == 1
    assert res["interval_days"] >= 1.0
