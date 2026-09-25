import copy
import re
from unittest.mock import MagicMock
import pytest

from src.contracts.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentResult,
    Evidence,
    StudentProfile,
    Student,
)
from src.assessment.service import (
    AssessmentService,
    trace_binary_search,
    parse_numeric_count,
    normalize_complexity,
    validate_question,
    idk_label,
)
from src.orchestration.factory import build_system


def _dummy_evidence(chunk_id="chunk-1", source_type="student_upload", text=None):
    return Evidence(
        chunk_id=chunk_id,
        text=text or "Binary search operates on a sorted indexed array. It compares the target key to the median element. Worst-case time complexity is O(log n).",
        source="sample_manual_lecture.txt",
        score=0.95,
        authority="lecture_material",
        trust_score=1.0,
        page=1,
        source_type=source_type,
        source_url=None if source_type == "student_upload" else "https://csd.cmu.edu",
        conflict=False,
        retrieval_method="hybrid",
        is_wikipedia=False,
    )


# 1. Selected material evidence is used
def test_selected_material_evidence_is_used():
    svc = AssessmentService()
    ev = _dummy_evidence()
    a = svc.generate(
        topic="Binary Search",
        concepts=["binary search"],
        evidence=[ev],
        document_ids=["doc-123"],
        source_type="student_upload",
        source_title="sample_manual_lecture.txt",
    )
    assert a is not None
    assert a.source_type == "student_upload"
    assert a.source_title == "sample_manual_lecture.txt"
    assert all("chunk-1" in q.evidence_chunk_ids for q in a.questions)


# 2. Selected material prevents external search
def test_selected_material_prevents_external_search(tmp_path):
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-1", "Student", "CS", "en")
    f = tmp_path / "course.txt"
    f.write_text("Binary search operates on a sorted array.", encoding="utf-8")
    doc_id = ai.upload_document("s-1", f, "course.txt")

    ai.discovery.discover = MagicMock(side_effect=RuntimeError("External discovery must not be called!"))
    # Call with document_ids
    assessment = ai.create_assessment("s-1", "Binary Search", ["binary search"], document_ids=[doc_id])
    assert assessment is not None
    assert assessment.source_type == "student_upload"
    ai.discovery.discover.assert_not_called()


# 3. No material uses trusted external accepted evidence
def test_no_material_uses_trusted_external_accepted_evidence(tmp_path):
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-ext", "External Student", "CS", "en")
    assessment = ai.create_assessment("s-ext", "Binary Search", ["binary search"], document_ids=[])
    assert assessment is not None
    assert assessment.source_type == "trusted_external"
    assert all(q.source_type == "trusted_external" for q in assessment.questions)


# 4. No evidence causes refusal
def test_no_evidence_causes_refusal():
    svc = AssessmentService()
    res = svc.generate("Quantum Algorithms", ["qubits"], evidence=[])
    assert res is None


# 5. No model-memory assessment fallback
def test_no_model_memory_assessment_fallback(tmp_path):
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-refusal", "Refusal Student", "CS", "en")
    # Simulate external search failing / returning 0 results
    ai.discovery.discover = MagicMock(return_value=([], "unavailable:HTTPStatusError", "trusted_external"))
    res = ai.create_assessment("s-refusal", "Arbitrary Topic", ["topic"], document_ids=[])
    assert res is None


# 6. Unsupported question is rejected
def test_unsupported_question_is_rejected():
    q = AssessmentQuestion(
        question_id="q-unsupported",
        concept="random concept",
        kind="short",
        prompt="Tell me about something unsupported.",
        expected="some unsupported claim",
        # Missing provenance
        source_type=None,
        evidence_chunk_ids=[],
        source_title=None,
    )
    is_valid, msg = validate_question(q)
    assert not is_valid
    assert "Missing" in msg


# 7. Provenance is required
def test_provenance_is_required():
    q = AssessmentQuestion(
        question_id="q-prov",
        concept="sorting",
        kind="short",
        prompt="Why sorted?",
        expected="Array must be sorted.",
        source_type="student_upload",
        source_title="lecture.txt",
        evidence_chunk_ids=["chunk-1"],
        verification_method="exact_evidence_fact",
    )
    is_valid, msg = validate_question(q)
    assert is_valid, msg


# 8. Missing provenance cannot reach UI-ready assessment
def test_missing_provenance_cannot_reach_ui_ready_assessment():
    svc = AssessmentService()
    ev = _dummy_evidence()
    a = svc.generate("Binary Search", ["binary search"], evidence=[ev], document_ids=["doc-1"])
    assert a is not None
    for q in a.questions:
        assert q.source_type in ("student_upload", "trusted_external")
        assert len(q.evidence_chunk_ids) > 0
        assert q.source_title is not None
        assert q.verification_method is not None


# 9. Source_type cannot silently default to student_upload
def test_source_type_cannot_silently_default_to_student_upload():
    q = AssessmentQuestion(
        question_id="q-def",
        concept="concept",
        kind="short",
        prompt="Prompt?",
        expected="Answer.",
    )
    assert q.source_type is None
    is_valid, _ = validate_question(q)
    assert not is_valid


# 10. Expected answer is grounded
def test_expected_answer_is_grounded():
    ev = _dummy_evidence(text="The time complexity of binary search is O(log n).")
    svc = AssessmentService()
    a = svc.generate("Binary Search", ["binary search"], evidence=[ev], document_ids=["doc-1"])
    assert a is not None
    time_q = next((q for q in a.questions if "complexity" in q.concept.lower()), None)
    assert time_q is not None
    assert "O(log n)" in time_q.expected


# 11. MCQ has exactly one correct option
def test_mcq_has_exactly_one_correct_option():
    q = AssessmentQuestion(
        question_id="mcq-valid",
        concept="prerequisite",
        kind="mcq",
        prompt="What is required?",
        options=["Strictly sorted array", "Unsorted array", "I don't know"],
        expected="Strictly sorted array",
        source_type="student_upload",
        source_title="doc.txt",
        evidence_chunk_ids=["c-1"],
        verification_method="exact_evidence_fact",
    )
    is_valid, _ = validate_question(q)
    assert is_valid


# 12. Ambiguous MCQ rejected
def test_ambiguous_mcq_rejected():
    q = AssessmentQuestion(
        question_id="mcq-ambiguous",
        concept="prerequisite",
        kind="mcq",
        prompt="What is required?",
        options=["Strictly sorted array", "Strictly sorted array", "I don't know"],
        expected="Strictly sorted array",
        source_type="student_upload",
        source_title="doc.txt",
        evidence_chunk_ids=["c-1"],
        verification_method="exact_evidence_fact",
    )
    is_valid, msg = validate_question(q)
    assert not is_valid
    assert "exactly one" in msg


# 13. Binary Search trace computes 3 comparisons
def test_binary_search_trace_computes_3():
    arr = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
    res = trace_binary_search(arr, 23)
    assert res["found"] is True
    assert res["comparisons"] == 3
    # Verify trace steps
    assert res["trace"][0]["mid_value"] == 16
    assert res["trace"][1]["mid_value"] == 56
    assert res["trace"][2]["mid_value"] == 23


# 14. LLM expected=2 vs deterministic=3 causes candidate rejection
def test_llm_expected_2_vs_deterministic_3_causes_candidate_rejection():
    # LLM hallucinates expected="2 comparisons" for an exercise requiring 3
    q = AssessmentQuestion(
        question_id="q-hallucinated",
        concept="binary search trace",
        kind="short",
        prompt="Given array [2, 5, 8, 12, 16, 23, 38, 56, 72, 91] and target value 23, how many comparisons are made?",
        expected="2 comparisons",
        source_type="student_upload",
        source_title="doc.txt",
        evidence_chunk_ids=["c-1"],
        verification_method="deterministic_trace",
    )
    is_valid, msg = validate_question(q)
    # MUST be rejected, never silently overwritten
    assert not is_valid
    assert "Deterministic mismatch" in msg


# 15. "3 comparisons" grades correct
def test_three_comparisons_grades_correct():
    svc = AssessmentService()
    q = AssessmentQuestion(
        question_id="q-eval",
        concept="binary search trace",
        kind="short",
        prompt="Given array [2, 5, 8, 12, 16, 23, 38, 56, 72, 91] and target value 23, how many comparisons are made?",
        expected="3 comparisons",
        source_type="student_upload",
        source_title="doc.txt",
        evidence_chunk_ids=["c-1"],
        verification_method="deterministic_trace",
    )
    assert svc._local_score(q, "3 comparisons") == 1.0
    assert svc._local_score(q, "3") == 1.0
    assert svc._local_score(q, "3 steps") == 1.0
    assert svc._local_score(q, "three comparisons") == 1.0


# 16. Wrong answer maps to focus area
def test_wrong_answer_maps_to_focus_area():
    svc = AssessmentService()
    q = AssessmentQuestion(
        question_id="q-w",
        concept="binary search trace",
        kind="short",
        prompt="Count comparisons?",
        expected="3 comparisons",
        source_type="student_upload",
        source_title="doc.txt",
        evidence_chunk_ids=["c-1"],
        verification_method="deterministic_trace",
    )
    a = Assessment(assessment_id="a-w", topic="Binary Search", questions=[q])
    res = svc.analyze(a, {"q-w": "5 comparisons"})
    assert res.score == 0.0
    assert "binary search trace" in res.weak_concepts
    assert res.misconceptions == []


# 17. I Don't Know maps to missing knowledge
def test_idk_maps_to_missing_knowledge():
    svc = AssessmentService()
    q = AssessmentQuestion(
        question_id="q-idk",
        concept="median comparison",
        kind="short",
        prompt="Explain median comparison?",
        expected="Compares target key with median element.",
        source_type="student_upload",
        source_title="doc.txt",
        evidence_chunk_ids=["c-1"],
        verification_method="exact_evidence_fact",
    )
    a = Assessment(assessment_id="a-idk", topic="Binary Search", questions=[q])
    res = svc.analyze(a, {"q-idk": "I don't know"})
    assert res.score == 0.0
    assert "median comparison" in res.unknown_concepts


# 18. I Don't Know is not misconception
def test_idk_is_not_misconception():
    svc = AssessmentService()
    q = AssessmentQuestion(
        question_id="q-idk-2",
        concept="pooling",
        kind="short",
        prompt="Explain pooling?",
        expected="Reduces spatial dimensions.",
        source_type="student_upload",
        source_title="doc.txt",
        evidence_chunk_ids=["c-1"],
        verification_method="exact_evidence_fact",
    )
    a = Assessment(assessment_id="a-idk-2", topic="CNN", questions=[q])
    res = svc.analyze(a, {"q-idk-2": "I don't know"})
    assert res.misconceptions == []


# 19. Ordinary numeric mistake is not automatically misconception
def test_ordinary_numeric_mistake_is_not_automatically_misconception():
    svc = AssessmentService()
    q = AssessmentQuestion(
        question_id="q-num-err",
        concept="binary search trace",
        kind="short",
        prompt="How many comparisons?",
        expected="3 comparisons",
        source_type="student_upload",
        source_title="doc.txt",
        evidence_chunk_ids=["c-1"],
        verification_method="deterministic_trace",
    )
    a = Assessment(assessment_id="a-num", topic="Binary Search", questions=[q])
    # Student incorrectly says 2 instead of 3
    res = svc.analyze(a, {"q-num-err": "2 comparisons"})
    assert res.score == 0.0
    assert res.misconceptions == []
    assert "binary search trace" in res.weak_concepts


# 20. Correct + Wrong + Unknown + Correct = exactly 50%
def test_correct_wrong_unknown_correct_grades_50_percent():
    svc = AssessmentService()
    q1 = AssessmentQuestion(
        question_id="q1", concept="c1", kind="short", prompt="p1", expected="correct one",
        source_type="student_upload", source_title="doc", evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    q2 = AssessmentQuestion(
        question_id="q2", concept="c2", kind="short", prompt="p2", expected="correct two",
        source_type="student_upload", source_title="doc", evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    q3 = AssessmentQuestion(
        question_id="q3", concept="c3", kind="short", prompt="p3", expected="correct three",
        source_type="student_upload", source_title="doc", evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    q4 = AssessmentQuestion(
        question_id="q4", concept="c4", kind="short", prompt="p4", expected="3 comparisons",
        source_type="student_upload", source_title="doc", evidence_chunk_ids=["c1"], verification_method="deterministic_trace"
    )
    a = Assessment(assessment_id="a-50", topic="Test Topic", questions=[q1, q2, q3, q4])
    answers = {
        "q1": "correct one",      # 1.0 (Correct)
        "q2": "completely wrong",  # 0.0 (Wrong)
        "q3": "I don't know",     # 0.0 (Unknown)
        "q4": "3 comparisons",    # 1.0 (Correct)
    }
    res = svc.analyze(a, answers)
    assert res.score == 0.50


# 21. O(log n) formatting variants normalize correctly
def test_ologn_formatting_variants_normalize_correctly():
    svc = AssessmentService()
    q = AssessmentQuestion(
        question_id="q-comp", concept="complexity", kind="short", prompt="Complexity?",
        expected="O(log n)", source_type="student_upload", source_title="doc", evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    variants = ["O(log n)", "O(log(n))", "O(logn)", "O(log_2 n)", "O(log2 n)", "$O(\\log n)$"]
    for var in variants:
        assert svc._local_score(q, var) == 1.0, f"Variant {var} should score 1.0"


# 22. Little-o is not treated as Big-O
def test_little_o_is_not_treated_as_big_o():
    svc = AssessmentService()
    q = AssessmentQuestion(
        question_id="q-o", concept="complexity", kind="short", prompt="Complexity?",
        expected="O(log n)", source_type="student_upload", source_title="doc", evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    # o(log n) is strictly distinct from O(log n)
    assert svc._local_score(q, "o(log n)") == 0.0
    assert svc._local_score(q, "o(logn)") == 0.0


# 23. Theta accepted only when rubric allows it
def test_theta_accepted_only_when_rubric_allows():
    svc = AssessmentService()
    q_no_theta = AssessmentQuestion(
        question_id="q-nt", concept="complexity", kind="short", prompt="Complexity?",
        expected="O(log n)", rubric="Only upper bound tested.",
        source_type="student_upload", source_title="doc", evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    assert svc._local_score(q_no_theta, "Θ(log n)") == 0.0
    assert svc._local_score(q_no_theta, "Theta(log n)") == 0.0

    q_theta_ok = AssessmentQuestion(
        question_id="q-tok", concept="complexity", kind="short", prompt="Complexity?",
        expected="O(log n)", rubric="Tight bound Theta(log n) is acceptable.",
        source_type="student_upload", source_title="doc", evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    assert svc._local_score(q_theta_ok, "Θ(log n)") == 1.0
    assert svc._local_score(q_theta_ok, "Theta(log n)") == 1.0


# 24. Semantic grader receives supporting evidence
def test_semantic_grader_receives_supporting_evidence():
    svc = AssessmentService()
    q = AssessmentQuestion(
        question_id="q-sem", concept="divide and conquer", kind="short", prompt="Explain the strategy?",
        expected="Halves search space each step.", rubric="Grade strictly based on evidence.",
        source_type="student_upload", source_title="lecture.txt",
        evidence_chunk_ids=["c-1"], evidence_excerpt="Repeatedly divides the search interval in half.",
        verification_method="semantic_rubric"
    )
    a = Assessment(assessment_id="a-sem", topic="Binary Search", questions=[q])

    mock_llm = MagicMock()
    mock_llm.is_mock = False
    mock_llm.generate_json = MagicMock(return_value={
        "items": [{"question_id": "q-sem", "score": 0.85, "misconception": None, "reason": "Good alignment"}]
    })

    res = svc.analyze(a, {"q-sem": "It splits the search range into two equal parts repeatedly."}, llm=mock_llm)
    assert res.score == 0.85
    mock_llm.generate_json.assert_called_once()
    call_prompt = mock_llm.generate_json.call_args[0][1]
    assert "Repeatedly divides the search interval in half." in call_prompt


# 25. Profile update is atomic
def test_profile_update_is_atomic(tmp_path):
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-atomic", "Atomic Student", "CS", "en")
    q = AssessmentQuestion(
        question_id="q1", concept="binary search", kind="short", prompt="Explain?",
        expected="Searches sorted array.", source_type="student_upload", source_title="doc",
        evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    a = Assessment(assessment_id="a-atomic", topic="Binary Search", questions=[q])
    res = ai.submit_assessment("s-atomic", a, {"q1": "Searches sorted array."})
    assert res.score == 1.0
    p = ai.get_student_profile("s-atomic")
    assert p.concept_mastery["binary search"] == 1.0
    assert len(p.assessment_history) == 1


# 26. Grading failure leaves original in-memory profile unchanged
def test_grading_failure_leaves_original_in_memory_profile_unchanged(tmp_path):
    ai = build_system(str(tmp_path), test_mode=True)
    p_orig = ai.create_or_load_student("s-fail", "Fail Student", "CS", "en")
    p_orig.concept_mastery["existing"] = 0.9

    q = AssessmentQuestion(
        question_id="q-err", concept="broken", kind="short", prompt="Err?",
        expected="Valid", source_type="student_upload", source_title="doc",
        evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    a = Assessment(assessment_id="a-err", topic="Broken", questions=[q])

    # Inject failure into analyze
    ai.assess.analyze = MagicMock(side_effect=RuntimeError("Grading engine crashed!"))

    with pytest.raises(RuntimeError):
        ai.submit_assessment("s-fail", a, {"q-err": "Valid"})

    # Original in-memory profile must be unmodified
    assert p_orig.concept_mastery == {"existing": 0.9}
    assert p_orig.assessment_history == []


# 27. Grading failure leaves persisted profile unchanged
def test_grading_failure_leaves_persisted_profile_unchanged(tmp_path):
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("s-disk", "Disk Student", "CS", "en")

    q = AssessmentQuestion(
        question_id="q-err-disk", concept="broken", kind="short", prompt="Err?",
        expected="Valid", source_type="student_upload", source_title="doc",
        evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    a = Assessment(assessment_id="a-disk-err", topic="Broken", questions=[q])

    # Inject failure before persistence
    ai.store.save = MagicMock(side_effect=IOError("Disk write failed!"))

    with pytest.raises(IOError):
        ai.submit_assessment("s-disk", a, {"q-err-disk": "Valid"})

    # Profile on disk must still be in initial state
    fresh_p = ai.store.load("s-disk")
    assert fresh_p.assessment_history == []
    assert fresh_p.concept_mastery == {}


# 28. Assessment material selector maps filename to internal doc_id and generates grounded questions
def test_assessment_material_selection_mapping(tmp_path):
    from src.integration import build_module
    mod = build_module(data_dir=str(tmp_path), test_mode=True)
    mod.sync_learning_context("s-ui", "UI Learner", "CS101", "en")

    # Ingest lecture material
    f = tmp_path / "sample_lecture.txt"
    f.write_text("Binary search operates on a sorted indexed array.", encoding="utf-8")
    meta = mod.upload_course_material("s-ui", f, "sample_lecture.txt")

    # Simulate UI material selector mapping
    materials = mod.list_course_materials("s-ui")
    assessment_label_to_id = {m.filename: m.document_id for m in materials}
    selected_labels = ["sample_lecture.txt"]
    assessment_doc_ids = [
        assessment_label_to_id[label]
        for label in selected_labels
        if label in assessment_label_to_id
    ]

    assert assessment_doc_ids == [meta.document_id]

    diag = mod.create_diagnostic("s-ui", "Binary Search", "en", document_ids=assessment_doc_ids)
    assert diag is not None
    assert diag.source_type == "student_upload"
    assert diag.source_title == "sample_lecture.txt"
    assert len(diag.questions) >= 1
    assert all(q.source_type == "student_upload" for q in diag.questions)
    assert all(q.document_id == meta.document_id for q in diag.questions)


# 29. Assessment empty selection maps to empty list and uses trusted external search
def test_assessment_empty_selection_uses_trusted_external(tmp_path):
    from src.integration import build_module
    mod = build_module(data_dir=str(tmp_path), test_mode=True)
    mod.sync_learning_context("s-ui-ext", "UI Ext Learner", "CS101", "en")

    # Empty selector maps to empty document_ids
    assessment_selected_labels = []
    assessment_label_to_id = {"dummy.txt": "dummy-id"}
    assessment_doc_ids = [
        assessment_label_to_id[label]
        for label in assessment_selected_labels
        if label in assessment_label_to_id
    ]

    assert assessment_doc_ids == []

    diag = mod.create_diagnostic("s-ui-ext", "Binary Search", "en", document_ids=assessment_doc_ids)
    assert diag is not None
    assert diag.source_type == "trusted_external"
    assert all(q.source_type == "trusted_external" for q in diag.questions)


# 30. Complexity grading router: mathematical precision & no LLM fallback on parseable expressions
def test_complexity_grading_router_mathematical_precision():
    svc = AssessmentService()
    q_const = AssessmentQuestion(
        question_id="q-c1", concept="space complexity", kind="short", prompt="Space complexity?",
        expected="O(1)", source_type="student_upload", source_title="doc",
        evidence_chunk_ids=["c1"], verification_method="complexity_notation"
    )
    # O(1) vs O(1) -> 1.0
    assert svc._local_score(q_const, "O(1)") == 1.0
    # O(1) vs O(n) -> 0.0
    assert svc._local_score(q_const, "O(n)") == 0.0

    q_n = AssessmentQuestion(
        question_id="q-n", concept="time complexity", kind="short", prompt="Time complexity?",
        expected="O(n)", source_type="student_upload", source_title="doc",
        evidence_chunk_ids=["c1"], verification_method="complexity_notation"
    )
    # O(n) vs O(n^2) -> 0.0
    assert svc._local_score(q_n, "O(n^2)") == 0.0

    q_log = AssessmentQuestion(
        question_id="q-log", concept="time complexity", kind="short", prompt="Time complexity?",
        expected="O(log n)", source_type="student_upload", source_title="doc",
        evidence_chunk_ids=["c1"], verification_method="complexity_notation"
    )
    # O(log n) vs O(log(n)) -> 1.0
    assert svc._local_score(q_log, "O(log(n))") == 1.0
    # little-o vs Big-O -> 0.0
    assert svc._local_score(q_log, "o(log n)") == 0.0

    # Theta rubric-dependent
    q_theta_strict = AssessmentQuestion(
        question_id="q-ts", concept="time complexity", kind="short", prompt="Time complexity?",
        expected="O(log n)", rubric="Strict upper bound.",
        source_type="student_upload", source_title="doc",
        evidence_chunk_ids=["c1"], verification_method="complexity_notation"
    )
    assert svc._local_score(q_theta_strict, "Θ(log n)") == 0.0

    q_theta_perm = AssessmentQuestion(
        question_id="q-tp", concept="time complexity", kind="short", prompt="Time complexity?",
        expected="O(log n)", rubric="Tight bound Theta accepted.",
        source_type="student_upload", source_title="doc",
        evidence_chunk_ids=["c1"], verification_method="complexity_notation"
    )
    assert svc._local_score(q_theta_perm, "Θ(log n)") == 1.0

    # Parseable correct and wrong complexity answers do NOT call LLM grader
    mock_llm = MagicMock()
    mock_llm.is_mock = False
    mock_llm.generate_json = MagicMock()

    a = Assessment(assessment_id="a-comp", topic="Algorithms", questions=[q_const])
    res_correct = svc.analyze(a, {"q-c1": "O(1)"}, llm=mock_llm)
    assert res_correct.score == 1.0
    mock_llm.generate_json.assert_not_called()

    res_wrong = svc.analyze(a, {"q-c1": "O(n)"}, llm=mock_llm)
    assert res_wrong.score == 0.0
    mock_llm.generate_json.assert_not_called()


# 31. Numeric trace grading router: deterministic count & no LLM fallback
def test_numeric_grading_router_mathematical_precision():
    svc = AssessmentService()
    q_num = AssessmentQuestion(
        question_id="q-num", concept="binary search trace", kind="short", prompt="How many comparisons are made?",
        expected="3 comparisons", source_type="student_upload", source_title="doc",
        evidence_chunk_ids=["c1"], verification_method="deterministic_trace"
    )
    # 3 comparisons vs 3 -> 1.0
    assert svc._local_score(q_num, "3 comparisons") == 1.0
    assert svc._local_score(q_num, "3") == 1.0
    assert svc._local_score(q_num, "three comparisons") == 1.0
    # 2 vs 3 -> 0.0
    assert svc._local_score(q_num, "2") == 0.0
    assert svc._local_score(q_num, "2 comparisons") == 0.0

    # Wrong parseable numeric answer does NOT call LLM grader
    mock_llm = MagicMock()
    mock_llm.is_mock = False
    mock_llm.generate_json = MagicMock()

    a = Assessment(assessment_id="a-num", topic="Algorithms", questions=[q_num])
    res_wrong = svc.analyze(a, {"q-num": "2 comparisons"}, llm=mock_llm)
    assert res_wrong.score == 0.0
    mock_llm.generate_json.assert_not_called()


# 32. MCQ grading router: deterministic only & no LLM fallback
def test_mcq_grading_router_deterministic():
    svc = AssessmentService()
    q_mcq = AssessmentQuestion(
        question_id="q-mcq", concept="prerequisite", kind="mcq",
        prompt="Which condition is required for binary search?",
        options=["The array must be strictly sorted.", "The array must be unsorted.", "I don't know"],
        expected="The array must be strictly sorted.", source_type="student_upload", source_title="doc",
        evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    # Correct -> 1.0
    assert svc._local_score(q_mcq, "The array must be strictly sorted.") == 1.0
    # Wrong -> 0.0
    assert svc._local_score(q_mcq, "The array must be unsorted.") == 0.0

    # LLM grader not called
    mock_llm = MagicMock()
    mock_llm.is_mock = False
    mock_llm.generate_json = MagicMock()

    a = Assessment(assessment_id="a-mcq", topic="Algorithms", questions=[q_mcq])
    res_wrong = svc.analyze(a, {"q-mcq": "The array must be unsorted."}, llm=mock_llm)
    assert res_wrong.score == 0.0
    mock_llm.generate_json.assert_not_called()


# 33. I Don't Know grading router: deterministic missing knowledge, no misconception, no LLM
def test_idk_grading_router_deterministic():
    svc = AssessmentService()
    q = AssessmentQuestion(
        question_id="q-idk", concept="worst-case complexity", kind="short", prompt="Worst-case complexity?",
        expected="O(log n)", source_type="student_upload", source_title="doc",
        evidence_chunk_ids=["c1"], verification_method="complexity_notation"
    )
    mock_llm = MagicMock()
    mock_llm.is_mock = False
    mock_llm.generate_json = MagicMock()

    a = Assessment(assessment_id="a-idk", topic="Algorithms", questions=[q])
    res = svc.analyze(a, {"q-idk": "I don't know"}, llm=mock_llm)
    assert res.score == 0.0
    assert "worst-case complexity" in res.unknown_concepts
    assert res.misconceptions == []
    mock_llm.generate_json.assert_not_called()


# 34. Exact manual binary search scenario reconstruction: 1 + 1 + 0 + 0 = exactly 50%
def test_exact_manual_binary_search_scenario_reconstruction():
    svc = AssessmentService()
    q1 = AssessmentQuestion(
        question_id="q1", concept="Binary Search", kind="mcq",
        prompt="Which condition must be met before binary search can be applied?",
        options=["The array must be strictly sorted.", "The array must be linked.", "I don't know"],
        expected="The array must be strictly sorted.",
        source_type="student_upload", source_title="sample_manual_lecture.txt",
        evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    q2 = AssessmentQuestion(
        question_id="q2", concept="binary search trace", kind="short",
        prompt="Trace binary search for target 9 in [1, 3, 5, 7, 9, 11, 13]. How many comparisons are made?",
        expected="3 comparisons",
        source_type="student_upload", source_title="sample_manual_lecture.txt",
        evidence_chunk_ids=["c1"], verification_method="deterministic_trace"
    )
    q3 = AssessmentQuestion(
        question_id="q3", concept="worst-case complexity", kind="short",
        prompt="What is the worst-case time complexity of binary search?",
        expected="O(log n)",
        source_type="student_upload", source_title="sample_manual_lecture.txt",
        evidence_chunk_ids=["c1"], verification_method="complexity_notation"
    )
    q4 = AssessmentQuestion(
        question_id="q4", concept="space complexity", kind="short",
        prompt="What is the auxiliary space complexity of an iterative implementation of binary search?",
        expected="O(1)",
        source_type="student_upload", source_title="sample_manual_lecture.txt",
        evidence_chunk_ids=["c1"], verification_method="complexity_notation"
    )

    assessment = Assessment(
        assessment_id="test-manual-binary-search",
        topic="Binary Search",
        questions=[q1, q2, q3, q4],
        source_type="student_upload",
        source_title="sample_manual_lecture.txt"
    )

    student_answers = {
        "q1": "The array must be strictly sorted.",
        "q2": "3 comparisons",
        "q3": "I don't know",
        "q4": "O(n)"
    }

    mock_llm = MagicMock()
    mock_llm.is_mock = False
    mock_llm.generate_json = MagicMock()

    res = svc.analyze(assessment, student_answers, llm=mock_llm)

    # Q1 = 1.0, Q2 = 1.0, Q3 = 0.0, Q4 = 0.0 -> Total = 50%
    assert res.score == 0.50
    assert res.concept_mastery["Binary Search"] == 1.0
    assert res.concept_mastery["binary search trace"] == 1.0
    assert res.concept_mastery["worst-case complexity"] == 0.0
    assert res.concept_mastery["space complexity"] == 0.0

    # Q4: Focus Area (weak concept), NOT strong area
    assert "space complexity" in res.weak_concepts
    assert "space complexity" not in res.strengths

    # Q3: Missing Knowledge
    assert "worst-case complexity" in res.unknown_concepts
    assert "worst-case complexity" in res.weak_concepts

    # Strengths: only mastered concepts
    assert set(res.strengths) == {"Binary Search", "binary search trace"}

    # No false misconceptions
    assert res.misconceptions == []

    # LLM grader must NOT be called for structured answers
    mock_llm.generate_json.assert_not_called()

