from __future__ import annotations

import datetime
from src.contracts.models import StudentProfile, Student
from src.personalization.orchestrator import LearningOrchestrator
from src.student_intelligence.spaced_repetition import SpacedRepetitionService


def _create_profile(**kwargs) -> StudentProfile:
    student = Student(
        student_id="test-student",
        name="Test Student",
        course="Computer Science",
        preferred_language="en",
        learning_preference="step-by-step",
    )
    return StudentProfile(student=student, **kwargs)


# 1. Misconception exists -> Correct Misconception (Priority A)
def test_misconception_priority_correct_misconception():
    orch = LearningOrchestrator()
    profile = _create_profile(
        concept_mastery={"convolution": 0.3, "filters": 0.8},
        weak_concepts=["convolution"],
        misconceptions=["Student believes pooling increases spatial dimensions instead of downsampling."],
        prerequisite_gaps=["matrices"],
    )
    action = orch.next_action(profile)
    assert action.action == "correct_misconception"
    assert action.priority == "high"
    assert "misconception" in action.reason.lower()


# 2. Proven prerequisite exists -> Remediate Prerequisite (Priority B)
def test_proven_prerequisite_produces_remediate_prerequisite():
    orch = LearningOrchestrator()
    # Explicit prerequisite relationship: sorting -> binary search
    profile = _create_profile(
        concept_mastery={"sorting": 0.2, "binary search": 0.5},
        weak_concepts=["sorting", "binary search"],
        prerequisite_gaps=["sorting"],
        misconceptions=[],
    )
    action = orch.next_action(profile)
    assert action.action == "remediate_prerequisite"
    assert action.priority == "high"
    assert "sorting" in action.target_concepts
    assert "prerequisite" in action.reason.lower()


# 3. Low mastery WITHOUT prerequisite relationship -> MUST NOT produce Remediate Prerequisite
def test_low_mastery_without_prerequisite_relation_never_produces_remediate_prerequisite():
    orch = LearningOrchestrator()
    # space complexity has low mastery and was naively placed in prerequisite_gaps
    profile = _create_profile(
        concept_mastery={"Binary search": 1.0, "space complexity": 0.0},
        weak_concepts=["space complexity"],
        prerequisite_gaps=["space complexity"],  # Unproven
        misconceptions=[],
    )
    action = orch.next_action(profile)
    assert action.action != "remediate_prerequisite"
    assert action.action == "targeted_remediation"
    assert action.target_concepts == ["space complexity"]


# 4. Missing knowledge (I don't know) -> Build Foundation (Priority C)
def test_missing_knowledge_produces_build_foundation():
    orch = LearningOrchestrator()
    profile = _create_profile(
        concept_mastery={"worst-case complexity": 0.0, "space complexity": 0.0},
        weak_concepts=["worst-case complexity", "space complexity"],
        misconceptions=[],
        assessment_history=[{"unknown_concepts": ["worst-case complexity"]}],
    )
    action = orch.next_action(profile)
    assert action.action == "build_foundation"
    assert action.priority == "high"
    assert action.target_concepts == ["worst-case complexity"]
    assert "missing knowledge" in action.reason.lower()


# 5. Weak attempted concept -> Reinforce Weak Concept (Priority D)
def test_weak_attempted_concept_produces_targeted_remediation():
    orch = LearningOrchestrator()
    # Concept was attempted (not missing knowledge), no misconception, no prerequisite
    profile = _create_profile(
        concept_mastery={"space complexity": 0.3},
        weak_concepts=["space complexity"],
        misconceptions=[],
        assessment_history=[{"unknown_concepts": []}],
    )
    action = orch.next_action(profile)
    assert action.action == "targeted_remediation"
    assert action.priority == "medium"
    assert action.target_concepts == ["space complexity"]
    assert action.strategy in ("simple-step-by-step", "practice")


# 6. Strong concepts only -> Advance / higher-difficulty action (Priority F)
def test_strong_concepts_only_produces_advance():
    orch = LearningOrchestrator()
    profile = _create_profile(
        concept_mastery={"Binary search": 1.0, "binary search trace": 1.0},
        strengths=["Binary search", "binary search trace"],
        weak_concepts=[],
        misconceptions=[],
        recent_topics=["Algorithms and Data Structures"],
    )
    action = orch.next_action(profile)
    assert action.action == "progress"
    assert action.priority == "low"
    assert action.strategy == "higher-difficulty"


# 7. Mixed state: Misconception + Missing + Weak -> Deterministic priority ordering
def test_mixed_state_deterministic_priority_ordering():
    orch = LearningOrchestrator()

    # Step A: All 3 exist -> Misconception wins (Priority A)
    profile_all = _create_profile(
        concept_mastery={"convolution": 0.3, "worst-case complexity": 0.0, "space complexity": 0.2},
        weak_concepts=["convolution", "worst-case complexity", "space complexity"],
        misconceptions=["Student believes convolution is element-wise multiplication."],
        assessment_history=[{"unknown_concepts": ["worst-case complexity"]}],
    )
    action_a = orch.next_action(profile_all)
    assert action_a.action == "correct_misconception"

    # Step B: Misconception cleared -> Missing Knowledge wins over Weak Attempted (Priority C > D)
    profile_all.misconceptions = []
    action_c = orch.next_action(profile_all)
    assert action_c.action == "build_foundation"
    assert action_c.target_concepts == ["worst-case complexity"]

    # Step C: Missing knowledge resolved -> Weak Attempted Concept addressed (Priority D)
    profile_all.concept_mastery["worst-case complexity"] = 0.85
    action_d = orch.next_action(profile_all)
    assert action_d.action == "targeted_remediation"
    assert "space complexity" in action_d.target_concepts or "convolution" in action_d.target_concepts


# 8. Current accepted Binary Search scenario: Exact profile validation
def test_current_accepted_binary_search_scenario():
    orch = LearningOrchestrator()
    profile = _create_profile(
        concept_mastery={
            "Binary search": 1.0,
            "binary search trace": 1.0,
            "worst-case complexity": 0.0,
            "space complexity": 0.0,
        },
        strengths=["Binary search", "binary search trace"],
        weak_concepts=["worst-case complexity", "space complexity"],
        prerequisite_gaps=["space complexity"],  # Old unproven field
        misconceptions=[],
        assessment_history=[{
            "assessment_id": "05711241-8f8f-457f-84a7-33bdfb957e4c",
            "score": 0.5,
            "unknown_concepts": ["worst-case complexity"],
            "weak_concepts": ["worst-case complexity", "space complexity"],
        }],
    )
    action = orch.next_action(profile)

    # Must NOT produce Remediate Prerequisite for space complexity
    assert action.action != "remediate_prerequisite"

    # Must prioritize Missing Knowledge on worst-case complexity
    assert action.action == "build_foundation"
    assert action.target_concepts == ["worst-case complexity"]
    assert action.priority == "high"
    assert action.triggering_evidence is not None


# 9. Spaced repetition: Remembered does not mutate concept_mastery or weak_concepts
def test_spaced_repetition_does_not_overwrite_assessment_truth_incorrectly():
    sr = SpacedRepetitionService()
    profile = _create_profile(
        concept_mastery={"worst-case complexity": 0.0},
        weak_concepts=["worst-case complexity"],
        strengths=[],
    )

    # Initial review item added
    sr.update_queue(profile)

    # "remembered" click updates scheduling metadata ONLY; MUST NOT mutate assessment truth
    sr.record_review(profile, "worst-case complexity", remembered=True)
    assert profile.concept_mastery["worst-case complexity"] == 0.0
    assert "worst-case complexity" in profile.weak_concepts


# 10. Root Issue A: AssessmentService never manufactures false prerequisite gaps
def test_assessment_service_never_creates_false_prerequisite_without_relation():
    from unittest.mock import MagicMock
    from src.assessment.service import AssessmentService
    from src.contracts.models import Assessment, AssessmentQuestion

    svc = AssessmentService()
    questions = [
        AssessmentQuestion(
            question_id="q1", concept="Binary Search", kind="mcq",
            prompt="Which condition must be met?", options=["Sorted", "Linked", "I don't know"],
            expected="Sorted", source_type="student_upload", source_title="lecture.txt",
            evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
        ),
        AssessmentQuestion(
            question_id="q2", concept="binary search trace", kind="short",
            prompt="Trace binary search. How many comparisons?", expected="3 comparisons",
            source_type="student_upload", source_title="lecture.txt",
            evidence_chunk_ids=["c1"], verification_method="deterministic_trace"
        ),
        AssessmentQuestion(
            question_id="q3", concept="worst-case complexity", kind="short",
            prompt="What is worst-case time complexity?", expected="O(log n)",
            source_type="student_upload", source_title="lecture.txt",
            evidence_chunk_ids=["c1"], verification_method="complexity_notation"
        ),
        AssessmentQuestion(
            question_id="q4", concept="space complexity", kind="short",
            prompt="What is auxiliary space complexity?", expected="O(1)",
            source_type="student_upload", source_title="lecture.txt",
            evidence_chunk_ids=["c1"], verification_method="complexity_notation"
        ),
    ]
    assessment = Assessment(
        assessment_id="test-binary-search-root-a",
        topic="Binary Search",
        questions=questions,
        source_type="student_upload",
        source_title="lecture.txt"
    )
    student_answers = {
        "q1": "Sorted",
        "q2": "3 comparisons",
        "q3": "I don't know",
        "q4": "O(n)"
    }
    mock_llm = MagicMock()
    mock_llm.is_mock = False

    res = svc.analyze(assessment, student_answers, llm=mock_llm)

    # Must NOT manufacture space complexity as prerequisite gap
    assert res.prerequisite_gaps == []
    assert "worst-case complexity" in res.unknown_concepts
    assert "space complexity" in res.weak_concepts
    assert set(res.strengths) == {"Binary Search", "binary search trace"}

    # Recommendations must treat space complexity as weak concept needing worked example
    assert not any("prerequisite knowledge for space complexity" in r for r in res.recommendations)
    assert any("Review space complexity with a worked example" in r for r in res.recommendations)
    assert any("Learn or review worst-case complexity from the fundamentals" in r for r in res.recommendations)


# 11. Root Issue A: AssessmentService detects genuine prerequisite gap when relationship exists
def test_assessment_service_creates_prerequisite_gap_when_explicit_relation_exists():
    from unittest.mock import MagicMock
    from src.assessment.service import AssessmentService
    from src.contracts.models import Assessment, AssessmentQuestion

    svc = AssessmentService()
    questions = [
        AssessmentQuestion(
            question_id="q1", concept="sorting", kind="mcq",
            prompt="Is data sorted?", options=["Yes", "No", "I don't know"],
            expected="Yes", source_type="student_upload", source_title="lecture.txt",
            evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact",
            prerequisite_concepts=[]
        ),
        AssessmentQuestion(
            question_id="q2", concept="binary search", kind="short",
            prompt="Perform binary search", expected="found",
            source_type="student_upload", source_title="lecture.txt",
            evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact",
            prerequisite_concepts=["sorting"]
        ),
    ]
    assessment = Assessment(
        assessment_id="test-binary-search-prereq",
        topic="Binary Search",
        questions=questions,
        source_type="student_upload",
        source_title="lecture.txt"
    )
    student_answers = {
        "q1": "No",       # Fails prerequisite concept sorting
        "q2": "wrong"
    }
    mock_llm = MagicMock()
    mock_llm.is_mock = False

    res = svc.analyze(assessment, student_answers, llm=mock_llm)
    # sorting is an explicit prerequisite concept declared on q2
    assert "sorting" in res.prerequisite_gaps
    assert any("prerequisite knowledge for sorting" in r for r in res.recommendations)


# 12. Root Issue B: StudyPlannerService separates Missing Knowledge from Weak Attempted Concepts
def test_study_planner_builds_foundation_for_missing_and_reinforces_attempted():
    from src.student_intelligence.planner import StudyPlannerService

    planner = StudyPlannerService()
    profile = _create_profile(
        concept_mastery={
            "Binary search": 1.0,
            "binary search trace": 1.0,
            "worst-case complexity": 0.0,
            "space complexity": 0.0,
        },
        strengths=["Binary search", "binary search trace"],
        weak_concepts=["worst-case complexity", "space complexity"],
        unknown_concepts=["worst-case complexity"],
        prerequisite_gaps=[],
        misconceptions=[],
    )

    plan = planner.build_study_plan(profile)
    assert len(plan) == 2

    # Item 1: Missing Knowledge -> Build Foundation (High priority)
    assert plan[0]["title"] == "Build Foundation: worst-case complexity"
    assert plan[0]["priority"] == "high"
    assert "foundational learning is required" in plan[0]["reason"]

    # Item 2: Weak Attempted Concept -> Reinforce Weak Concept (Medium priority)
    assert plan[1]["title"] == "Reinforce Weak Concept: space complexity"
    assert plan[1]["priority"] == "medium"
    assert "below target threshold of 70%" in plan[1]["reason"]


# 13. Root Issue B: StudyPlannerService ignores unproven prerequisite gaps
def test_study_planner_filters_out_unproven_prerequisites():
    from src.student_intelligence.planner import StudyPlannerService

    planner = StudyPlannerService()
    profile = _create_profile(
        concept_mastery={"space complexity": 0.2},
        weak_concepts=["space complexity"],
        prerequisite_gaps=["space complexity"],  # Unproven
        misconceptions=[],
    )

    plan = planner.build_study_plan(profile)
    # Must NOT produce Remediate Prerequisite for space complexity
    assert not any("Remediate Prerequisite: space complexity" in p["title"] for p in plan)
    # Must produce Reinforce Weak Concept instead
    assert any(p["title"] == "Reinforce Weak Concept: space complexity" for p in plan)


# 14. Root Issue C: AITutor.submit_assessment persists unknown_concepts and rejects unproven prereqs
def test_ai_tutor_submit_assessment_persists_unknown_concepts_and_rejects_unproven_prereqs(tmp_path):
    from src.integration.service import build_system
    from src.contracts.models import Assessment, AssessmentQuestion

    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("test-s1", "Test Student")

    q1 = AssessmentQuestion(
        question_id="q1", concept="Binary Search", kind="mcq",
        prompt="Condition?", options=["Sorted", "Linked", "I don't know"],
        expected="Sorted", source_type="student_upload", source_title="lecture.txt",
        evidence_chunk_ids=["c1"], verification_method="exact_evidence_fact"
    )
    q2 = AssessmentQuestion(
        question_id="q2", concept="worst-case complexity", kind="short",
        prompt="Time complexity?", expected="O(log n)",
        source_type="student_upload", source_title="lecture.txt",
        evidence_chunk_ids=["c1"], verification_method="complexity_notation"
    )
    q3 = AssessmentQuestion(
        question_id="q3", concept="space complexity", kind="short",
        prompt="Space complexity?", expected="O(1)",
        source_type="student_upload", source_title="lecture.txt",
        evidence_chunk_ids=["c1"], verification_method="complexity_notation"
    )
    assessment = Assessment(
        assessment_id="test-persist-c",
        topic="Binary Search",
        questions=[q1, q2, q3],
        source_type="student_upload",
        source_title="lecture.txt"
    )
    answers = {"q1": "Sorted", "q2": "I don't know", "q3": "O(n)"}

    res = ai.submit_assessment("test-s1", assessment, answers)
    profile = ai.get_student_profile("test-s1")

    # AssessmentResult properties
    assert res.score == round(1.0 / 3.0, 3)
    assert res.prerequisite_gaps == []
    assert res.unknown_concepts == ["worst-case complexity"]

    # StudentProfile persisted properties
    assert profile.unknown_concepts == ["worst-case complexity"]
    assert profile.prerequisite_gaps == []
    assert "space complexity" in profile.weak_concepts
    assert "worst-case complexity" in profile.weak_concepts
    assert "Binary Search" in profile.strengths


# 15. Root Issue C: Assessment retake clears unknown_concepts once mastered
def test_ai_tutor_submit_assessment_clears_unknown_when_subsequently_mastered(tmp_path):
    from src.integration.service import build_system
    from src.contracts.models import Assessment, AssessmentQuestion

    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("test-s2", "Test Student")

    q = AssessmentQuestion(
        question_id="q1", concept="worst-case complexity", kind="short",
        prompt="Time complexity?", expected="O(log n)",
        source_type="student_upload", source_title="lecture.txt",
        evidence_chunk_ids=["c1"], verification_method="complexity_notation"
    )
    assessment1 = Assessment(
        assessment_id="test-clear-1", topic="Binary Search",
        questions=[q], source_type="student_upload", source_title="lecture.txt"
    )

    # Turn 1: student says "I don't know"
    ai.submit_assessment("test-s2", assessment1, {"q1": "I don't know"})
    p1 = ai.get_student_profile("test-s2")
    assert "worst-case complexity" in p1.unknown_concepts

    # Turn 2: student learns and answers correctly
    assessment2 = Assessment(
        assessment_id="test-clear-2", topic="Binary Search",
        questions=[q], source_type="student_upload", source_title="lecture.txt"
    )
    ai.submit_assessment("test-s2", assessment2, {"q1": "O(log n)"})
    p2 = ai.get_student_profile("test-s2")
    assert "worst-case complexity" not in p2.unknown_concepts
    assert "worst-case complexity" in p2.strengths


# ==============================================================================
# 12 REQUIRED SPACED REPETITION / ASSESSMENT-TRUTH SEPARATION TESTS
# ==============================================================================

# 1. Remembered updates review scheduling
def test_sr_1_remembered_updates_review_scheduling():
    sr = SpacedRepetitionService()
    profile = _create_profile(
        concept_mastery={"binary search": 1.0},
        strengths=["binary search"],
    )
    sr.update_queue(profile)
    before_item = next(i for i in profile.review_queue if i["concept"] == "binary search")
    before_rep = before_item["repetition"]

    item = sr.record_review(profile, "binary search", remembered=True)
    assert item["repetition"] == before_rep + 1
    assert item["interval_days"] >= 1.0
    assert item["last_reviewed"] is not None
    assert item["due_date"] is not None
    assert item["last_result"] == "remembered"


# 2. Forgot updates review scheduling
def test_sr_2_forgot_updates_review_scheduling():
    sr = SpacedRepetitionService()
    profile = _create_profile(
        concept_mastery={"binary search": 1.0},
        strengths=["binary search"],
    )
    sr.update_queue(profile)
    # Simulate an item with existing repetition
    sr.record_review(profile, "binary search", remembered=True)
    item_before = next(i for i in profile.review_queue if i["concept"] == "binary search")
    assert item_before["repetition"] >= 1

    item_after = sr.record_review(profile, "binary search", remembered=False)
    assert item_after["repetition"] == 0
    assert item_after["interval_days"] == 1.0
    assert item_after["ease_factor"] < item_before["ease_factor"]
    assert item_after["last_result"] == "forgot"


# 3. Remembered does NOT change concept_mastery
def test_sr_3_remembered_does_not_change_concept_mastery():
    sr = SpacedRepetitionService()
    profile = _create_profile(
        concept_mastery={"worst-case complexity": 0.0, "space complexity": 0.35},
        weak_concepts=["worst-case complexity", "space complexity"],
    )
    sr.record_review(profile, "worst-case complexity", remembered=True)
    sr.record_review(profile, "space complexity", remembered=True)

    # Mastery MUST remain strictly unchanged by self-reported reviews
    assert profile.concept_mastery["worst-case complexity"] == 0.0
    assert profile.concept_mastery["space complexity"] == 0.35


# 4. Forgot does NOT change concept_mastery
def test_sr_4_forgot_does_not_change_concept_mastery():
    sr = SpacedRepetitionService()
    profile = _create_profile(
        concept_mastery={"Binary search": 1.0, "binary search trace": 0.85},
        strengths=["Binary search", "binary search trace"],
    )
    sr.record_review(profile, "Binary search", remembered=False)
    sr.record_review(profile, "binary search trace", remembered=False)

    # Mastery MUST remain strictly unchanged
    assert profile.concept_mastery["Binary search"] == 1.0
    assert profile.concept_mastery["binary search trace"] == 0.85


# 5. Remembered does NOT remove unknown_concepts
def test_sr_5_remembered_does_not_remove_unknown_concepts():
    sr = SpacedRepetitionService()
    profile = _create_profile(
        concept_mastery={"worst-case complexity": 0.0},
        weak_concepts=["worst-case complexity"],
        unknown_concepts=["worst-case complexity"],
    )
    sr.record_review(profile, "worst-case complexity", remembered=True)
    assert "worst-case complexity" in profile.unknown_concepts


# 6. Forgot does NOT create weak concept
def test_sr_6_forgot_does_not_create_weak_concept():
    sr = SpacedRepetitionService()
    profile = _create_profile(
        concept_mastery={"Binary search": 1.0},
        strengths=["Binary search"],
        weak_concepts=[],
    )
    sr.record_review(profile, "Binary search", remembered=False)
    assert "Binary search" not in profile.weak_concepts
    assert profile.weak_concepts == []


# 7. Forgot does NOT remove strength
def test_sr_7_forgot_does_not_remove_strength():
    sr = SpacedRepetitionService()
    profile = _create_profile(
        concept_mastery={"Binary search": 1.0},
        strengths=["Binary search"],
    )
    sr.record_review(profile, "Binary search", remembered=False)
    assert "Binary search" in profile.strengths


# 8. Review action does NOT create misconception
def test_sr_8_review_action_does_not_create_misconception():
    sr = SpacedRepetitionService()
    profile = _create_profile(
        concept_mastery={"Binary search": 1.0, "space complexity": 0.0},
        misconceptions=[],
    )
    sr.record_review(profile, "space complexity", remembered=False)
    sr.record_review(profile, "Binary search", remembered=True)
    assert profile.misconceptions == []


# 9. Review action does NOT change prerequisite_gaps
def test_sr_9_review_action_does_not_change_prerequisite_gaps():
    sr = SpacedRepetitionService()
    profile = _create_profile(
        concept_mastery={"sorting": 0.2, "Binary search": 1.0},
        prerequisite_gaps=[],
    )
    sr.record_review(profile, "sorting", remembered=False)
    sr.record_review(profile, "Binary search", remembered=True)
    assert profile.prerequisite_gaps == []


# 10. Review action does NOT change assessment_history
def test_sr_10_review_action_does_not_change_assessment_history():
    import copy
    sr = SpacedRepetitionService()
    history_entry = {
        "assessment_id": "test-assess-1",
        "score": 0.50,
        "concept_mastery": {"Binary search": 1.0, "worst-case complexity": 0.0},
        "weak_concepts": ["worst-case complexity"],
        "prerequisite_gaps": [],
        "misconceptions": [],
        "strengths": ["Binary search"],
        "recommendations": ["Review fundamentals"],
        "unknown_concepts": ["worst-case complexity"],
        "source_type": "student_upload",
        "source_title": "sample_manual_lecture.txt",
    }
    profile = _create_profile(
        concept_mastery={"Binary search": 1.0, "worst-case complexity": 0.0},
        assessment_history=[copy.deepcopy(history_entry)],
    )

    sr.record_review(profile, "worst-case complexity", remembered=True)
    sr.record_review(profile, "Binary search", remembered=False)
    assert profile.assessment_history == [history_entry]


# 11. Review action does NOT change Assessment score
def test_sr_11_review_action_does_not_change_assessment_score():
    sr = SpacedRepetitionService()
    profile = _create_profile(
        concept_mastery={"Binary search": 1.0, "worst-case complexity": 0.0},
        performance_trend=[0.50],
        assessment_history=[{"score": 0.50}],
    )
    sr.record_review(profile, "worst-case complexity", remembered=True)
    sr.record_review(profile, "Binary search", remembered=False)
    assert profile.performance_trend == [0.50]
    assert profile.assessment_history[0]["score"] == 0.50


# 12. Current 50% profile remains identical after simulated review events except review metadata
def test_sr_12_current_50_percent_profile_remains_identical_after_simulated_reviews():
    import json
    import copy
    from src.contracts.models import StudentProfile
    from src.personalization.orchestrator import LearningOrchestrator
    from src.student_intelligence.planner import StudyPlannerService

    with open("data/profiles/student-001.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Use a working in-memory copy of the accepted profile fixture
    profile_before = StudentProfile.model_validate(copy.deepcopy(data))
    profile_under_test = StudentProfile.model_validate(copy.deepcopy(data))

    sr = SpacedRepetitionService()
    planner = StudyPlannerService()
    orch = LearningOrchestrator()

    # Pre-review NBA and Plan
    nba_before = orch.next_action(profile_before)
    plan_before = planner.build_study_plan(profile_before)
    assert nba_before.action == "build_foundation"
    assert nba_before.target_concepts == ["worst-case complexity"]
    assert plan_before[0]["title"] == "Build Foundation: worst-case complexity"
    assert plan_before[1]["title"] == "Reinforce Weak Concept: space complexity"

    # Simulate multiple review events:
    # 1. User says "Remembered" on worst-case complexity
    sr.record_review(profile_under_test, "worst-case complexity", remembered=True)
    # 2. User says "Forgot" on Binary search
    sr.record_review(profile_under_test, "Binary search", remembered=False)
    # 3. User says "Remembered" on space complexity
    sr.record_review(profile_under_test, "space complexity", remembered=True)

    # All Assessment-grounded fields MUST remain completely identical:
    assert profile_under_test.concept_mastery == profile_before.concept_mastery
    assert profile_under_test.strengths == profile_before.strengths
    assert profile_under_test.weak_concepts == profile_before.weak_concepts
    assert profile_under_test.unknown_concepts == profile_before.unknown_concepts
    assert profile_under_test.misconceptions == profile_before.misconceptions
    assert profile_under_test.prerequisite_gaps == profile_before.prerequisite_gaps
    assert profile_under_test.assessment_history == profile_before.assessment_history
    assert profile_under_test.performance_trend == profile_before.performance_trend

    # NBA must STILL be build_foundation on worst-case complexity
    nba_after = orch.next_action(profile_under_test)
    assert nba_after.action == "build_foundation"
    assert nba_after.target_concepts == ["worst-case complexity"]
    assert nba_after.priority == "high"

    # Plan items 1 and 2 must remain identical in priority and concept
    plan_after = planner.build_study_plan(profile_under_test)
    assert plan_after[0]["title"] == "Build Foundation: worst-case complexity"
    assert plan_after[0]["priority"] == "high"
    assert plan_after[1]["title"] == "Reinforce Weak Concept: space complexity"
    assert plan_after[1]["priority"] == "medium"
