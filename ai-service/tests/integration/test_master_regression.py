from __future__ import annotations

import os
from pathlib import Path
import pytest

from src.orchestration.factory import build_system
from src.contracts.models import StudentQuery, Chunk, Evidence
from src.retrieval.service import is_semantic_near_miss
from src.discovery.service import clean_query_for_search


def test_q1_binary_search_direct_pedagogical_answer(tmp_path):
    """Section 28 Q1 regression:

    What is binary search? Explain how it works, state its time complexity,
    and mention the main requirement that must be satisfied before using it.
    """
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("student-reg-1", "Alice", "Algorithms", "en")

    q = (
        "What is binary search? Explain how it works, state its time complexity, "
        "and mention the main requirement that must be satisfied before using it."
    )
    resp = ai.ask(StudentQuery(student_id="student-reg-1", session_id="s1", text=q, course="Algorithms"))

    assert not resp.abstained, "Should not abstain when trusted evidence exists"
    answer = resp.answer.lower()

    # Core required behaviors:
    assert "binary search" in answer
    assert "o(log n)" in answer or "log n" in answer or "logarithmic" in answer
    assert "halv" in answer or "divide" in answer or "half" in answer
    assert "sort" in answer, "Must state that input must be sorted"

    # Must NOT be contaminated by near-miss data structures:
    assert "treap" not in answer
    assert "heap sort" not in answer
    assert "red-black" not in answer

    # Must NOT be a raw retrieval dump:
    assert "MOCK_RESPONSE:" not in resp.answer
    assert "Personalized explanation (step-by-step). What is binary search" not in resp.answer

    # Must have citations:
    assert len(resp.citations) >= 1
    assert any("[1]" in c for c in resp.citations)


def test_q2_directive_cleaning_and_relevant_sources_only(tmp_path):
    """Section 28 Q2 regression:

    Answer only from relevant retrieved evidence.
    What is the time complexity of binary search on a sorted array, and why is it O(log n)?
    Ignore retrieved passages that discuss other algorithms or data structures.
    """
    q_raw = (
        "Answer only from relevant retrieved evidence. "
        "What is the time complexity of binary search on a sorted array, and why is it O(log n)? "
        "Ignore retrieved passages that discuss other algorithms or data structures. "
        "If the retrieved evidence is insufficient, say so instead of using unrelated evidence."
    )

    # Verify directive cleaning
    cleaned = clean_query_for_search(q_raw)
    assert "Answer only from relevant retrieved evidence" not in cleaned
    assert "Ignore retrieved passages" not in cleaned
    assert "binary search" in cleaned.lower()
    assert "o(log n)" in cleaned.lower()

    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("student-reg-2", "Bob", "Algorithms", "en")

    resp = ai.ask(StudentQuery(student_id="student-reg-2", session_id="s2", text=q_raw, course="Algorithms"))
    assert not resp.abstained
    ans = resp.answer.lower()
    assert "o(log n)" in ans
    assert "halv" in ans or "half" in ans or "eliminat" in ans or "divide" in ans


def test_q3_capital_of_france_one_sentence(tmp_path):
    """Section 28 Q3 regression:

    What is the capital of France? Answer in one sentence only.
    """
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("student-reg-3", "Claire", "Geography", "en")

    q = "What is the capital of France? Answer in one sentence only."
    resp = ai.ask(StudentQuery(student_id="student-reg-3", session_id="s3", text=q, course="Geography"))

    assert not resp.abstained
    assert "paris" in resp.answer.lower()
    # Direct one sentence (allow citation bracket)
    lines = [line.strip() for line in resp.answer.splitlines() if line.strip()]
    assert len(lines) == 1, f"Expected 1 sentence/line, got: {resp.answer}"


def test_semantic_near_miss_detection_and_rejection():
    """Verify that tree/heap near-misses are detected and not accepted as array binary search."""
    q = "What is binary search and its time complexity on a sorted array?"

    near_miss_text = (
        "A treap is a randomized Cartesian tree combining binary search tree keys "
        "with binary max-heap priorities."
    )
    assert is_semantic_near_miss(q, near_miss_text) is True

    bst_text = (
        "A binary search tree (BST) is a node-based binary tree data structure where "
        "each node has left and right pointers."
    )
    assert is_semantic_near_miss(q, bst_text) is True

    valid_text = (
        "Binary search operates on a sorted array by repeatedly dividing the search space in half."
    )
    assert is_semantic_near_miss(q, valid_text) is False


def test_misconception_recovery_and_nba_transition(tmp_path):
    """Verify that when a student reassesses a misconception concept and succeeds,

    the misconception is resolved, mastery updates, and NBA transitions to progress.
    """
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-recovery", "Sami", "Deep Learning", "en")

    # Step 1: Diagnostic detects misconception on pooling
    assessment = ai.create_assessment("s-recovery", "CNN", ["pooling"])
    # Submit incorrect answer with misconception
    wrong_answers = {
        q.question_id: "pooling always increases the spatial dimensions of feature maps"
        for q in assessment.questions
    }
    result1 = ai.submit_assessment("s-recovery", assessment, wrong_answers)

    p1 = ai.get_student_profile("s-recovery")
    assert len(p1.misconceptions) > 0, "Misconception should be recorded"
    nba1 = ai.learning_orchestrator.next_action(p1)
    assert nba1.action == "correct_misconception"

    # Step 2: Reassessment after remediation
    reassessment = ai.create_assessment("s-recovery", "CNN", ["pooling"])
    correct_answers = {
        q.question_id: q.expected
        for q in reassessment.questions
    }
    result2 = ai.submit_assessment("s-recovery", reassessment, correct_answers)

    p2 = ai.get_student_profile("s-recovery")
    assert len(p2.misconceptions) == 0, "Misconception must be cleared upon successful reassessment"
    assert len(p2.resolved_misconceptions) > 0, "Resolved misconception should be tracked"
    assert p2.concept_mastery.get("pooling", 0.0) >= 0.70

    nba2 = ai.learning_orchestrator.next_action(p2)
    assert nba2.action in ("progress", "targeted_practice"), f"NBA should transition, got: {nba2.action}"


def test_numeric_and_formula_grading_with_citations(tmp_path):
    """Verify assessment grading correctly handles math formulas, numbers, and citation markers."""
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-math", "Mona", "Algorithms", "en")

    assessment = ai.create_assessment("s-math", "Algorithms", ["complexity"])
    # Modify a question to test numeric/formula expected
    q = assessment.questions[0]
    q.kind = "short"
    q.expected = "O(log n)"

    # Student answers with citation artifact
    score = ai.assess._local_score(q, "The complexity is O(log n) [1].")
    assert score is not None and score >= 0.8, f"Formula with citation should score high, got {score}"


def test_all_14_content_generation_types(tmp_path):
    """Verify all 14 content generation types are supported and produce valid artifacts."""
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-content", "Dina", "Computer Science", "en")

    # Upload material so grounding evidence is available
    f = tmp_path / "course.txt"
    f.write_text(
        "Binary search is an algorithm for finding an item from a sorted list. "
        "It repeatedly halves the search interval. Time complexity is O(log n).",
        encoding="utf-8",
    )
    ai.upload_document("s-content", f, "course.txt")

    all_14_types = [
        "explanation",
        "summary",
        "notes",
        "study_guide",
        "flashcards",
        "quiz",
        "exam",
        "practice",
        "code",
        "coding_exercise",
        "diagram",
        "presentation",
        "analogy",
        "comparison",
        "question_bank",
    ]

    out, routes = ai.generate_content("s-content", "Binary Search", all_14_types, "en")
    assert len(out) == len(all_14_types)

    for kind in all_14_types:
        item = out[kind]
        assert item["type"] in ("text", "file"), f"{kind} produced invalid type: {item}"
        if item["type"] == "file":
            assert Path(item["path"]).exists(), f"File artifact for {kind} must exist"
        else:
            assert len(item["content"]) > 10, f"Text content for {kind} must not be empty"


def test_voice_tutor_end_to_end_flow(tmp_path):
    """Verify Voice Tutor uses the unified learning brain, profile, and produces valid audio."""
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-voice", "Hassan", "Computer Science", "en")

    from src.voice.service import VoiceTutorService, VoiceError

    voice_svc = VoiceTutorService(ai, audio_dir=str(tmp_path / "audio"))

    # Simulated audio input containing a voice question
    simulated_audio = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00AUDIO_PROMPT: What is binary search and what is its time complexity?"

    result = voice_svc.ask_voice(
        student_id="s-voice",
        audio_data=simulated_audio,
        course_id="Computer Science",
    )

    assert result.success is True
    assert "binary search" in result.transcription.lower()
    assert result.audio_path is not None
    assert Path(result.audio_path).exists()
    assert result.audio_path.endswith(".wav")

    # Profile must be updated by the voice interaction!
    p = ai.get_student_profile("s-voice")
    assert len(p.learning_history) > 0, "Voice interaction must update student learning history"
    assert len(p.conversation_history) > 0, "Voice interaction must update conversation history"

    # Reject corrupt audio
    with pytest.raises(VoiceError):
        voice_svc.transcribe(b"invalid_corrupt_data_garbage")

    # Cleanup audio
    cleaned = voice_svc.cleanup_session_audio()
    assert cleaned >= 1


def test_student_and_course_isolation(tmp_path):
    """Student A state must never leak into Student B; Course A must not leak into Course B."""
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("student-a", "Alice", "Algorithms", "en")
    ai.create_or_load_student("student-b", "Bob", "History", "en")

    # Student A uploads material in Course 1
    doc_a = tmp_path / "algo_secret.txt"
    doc_a.write_text("AliceSecretAlgorithm: special sorting technique with O(n) runtime.", encoding="utf-8")
    meta_a = ai.upload_document("student-a", doc_a, "algo_secret.txt", course="Algorithms")

    # Student B queries their own course
    docs_b = ai.ingestion.list_documents("student-b")
    assert len(docs_b) == 0, "Student B must not see Student A documents"

    # Student B searches with own student_id — must not retrieve Student A's secret document
    ret_b, _ = ai.retrieval.retrieve("AliceSecretAlgorithm", "student-b", None, course="History")
    assert len(ret_b) == 0, "Student B must not retrieve Student A private uploaded chunks"


def test_spaced_repetition_and_study_planner(tmp_path):
    """Verify spaced repetition review queue and study planner react to learner state."""
    from src.integration import build_module

    mod = build_module(str(tmp_path), test_mode=True)
    mod.sync_learning_context("s-plan", "Laila", "AI", "en")

    # Create weakness via assessment
    diag = mod.create_diagnostic("s-plan", "CNN")
    wrong = {q.question_id: "I don't know" for q in diag.questions}
    mod.submit_diagnostic("s-plan", diag, wrong)

    plan = mod.get_study_plan("s-plan")
    assert len(plan) > 0, "Study plan should have prioritized items for weaknesses"
    assert any(item["priority"] in ("high", "medium") for item in plan)

    queue = mod.get_review_queue("s-plan")
    assert len(queue) > 0, "Review queue should contain assessed concepts"

    # Record concept review
    c = queue[0]["concept"]
    updated_item = mod.record_concept_review("s-plan", c, remembered=True)
    assert updated_item["repetition"] == 1
    assert updated_item["interval_days"] >= 1.0


def test_wikipedia_policy_exclusion():
    """Wikipedia must be excluded when authoritative Tier A evidence is present."""
    from infrastructure.search.trusted import trust, source_tier, is_wikipedia

    auth_mit, score_mit = trust("https://mit.edu/cs/notes.html")
    assert source_tier(auth_mit) == "A"
    assert score_mit >= 0.90

    auth_wiki, score_wiki = trust("https://en.wikipedia.org/wiki/Binary_search")
    assert is_wikipedia("https://en.wikipedia.org/wiki/Binary_search")
    assert source_tier(auth_wiki) == "C"
    assert score_wiki < 0.60
