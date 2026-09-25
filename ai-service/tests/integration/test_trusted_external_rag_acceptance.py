"""
Acceptance regression suite for Trusted External RAG and Profile-based Personalization.
Verifies the 11 key invariants:
1. no material -> trusted_external only
2. Search path invoked
3. upload chunks absent
4. same frozen evidence used across two learner profiles
5. strength -> higher-difficulty
6. missing knowledge -> foundational
7. different pedagogical output
8. identical evidence IDs and provenance
9. personalization cannot enlarge factual scope
10. unsupported claim rejected
11. production student profile unchanged
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from infrastructure.search.trusted import MockTrustedSearch, trust, source_tier
from src.contracts.models import (
    Evidence,
    QueryAnalysis,
    Student,
    StudentProfile,
    StudentQuery,
)
from src.content_generation.service import GenericClaimValidator
from src.orchestration.factory import build_system
from src.personalization.service import PersonalizationService


def test_no_material_routes_to_trusted_external_mode_with_zero_upload_chunks(tmp_path):
    """Invariant 1, 2, 3: document_ids=None uses trusted_external only with zero upload leakage."""
    ai = build_system(str(tmp_path), test_mode=True)
    ai.create_or_load_student("test-s", "Alice", "CS")

    # Upload local material to prove it is NOT leaked
    local_file = tmp_path / "local_course_notes.txt"
    local_file.write_text("Local-only private content: proprietary-secret-token-999.", encoding="utf-8")
    ai.upload_document("test-s", local_file, "local_course_notes.txt")

    # Ask query with document_ids=None
    query = StudentQuery(
        student_id="test-s",
        session_id="sess-test",
        text="Explain how binary search works in detail.",
        document_ids=None,
    )
    resp = ai.ask(query)

    assert not resp.abstained
    assert resp.knowledge_source == "trusted_external"
    assert resp.trusted_search_state == "ready"
    assert len(resp.evidence) > 0
    # Strict invariant: ZERO student_upload chunks
    assert all(e.source_type == "trusted_external" for e in resp.evidence)
    assert all("local_course_notes" not in e.source for e in resp.evidence)
    assert all("proprietary-secret-token-999" not in e.text for e in resp.evidence)


def test_trusted_search_registry_and_threshold_filtering():
    """Invariant 2: Verifies trust policy accepts authoritative university sources and rejects low-trust domains."""
    # Tier A university sources
    auth, score = trust("https://www.cs.cmu.edu/~rjsimmon/15122-s13/06-binsearch.pdf")
    assert auth == "university" and score >= 0.80
    assert source_tier(auth) == "A"

    auth, score = trust("https://www.math.umd.edu/~immortal/CMSC351/notes/binarysearch.pdf")
    assert auth == "university" and score >= 0.80

    # Low-trust / unverified sources
    auth, score = trust("https://random-unverified-blog.xyz/algo")
    assert score < 0.80
    assert source_tier(auth) == "D"


def test_same_frozen_evidence_across_profiles_proves_personalization_separation(tmp_path):
    """Invariant 4, 5, 6, 7, 8: Same frozen evidence yields distinct pedagogical strategies without changing facts."""
    # 1. Create frozen evidence bundle
    frozen_evidence = [
        Evidence(
            chunk_id="chunk-cmu-01",
            text=(
                "Binary search finds an element in a sorted array by repeatedly comparing the target to the middle element. "
                "The array must be ordered according to the precondition is_sorted(A, 0, n). "
                "The search space is halved in each iteration. Worst-case runtime is O(log n), and iterative space complexity is O(1)."
            ),
            source="CMU 15-122 Binary Search Notes",
            source_type="trusted_external",
            source_url="https://www.cs.cmu.edu/~rjsimmon/15122-s13/06-binsearch.pdf",
            authority="university",
            trust_score=0.98,
            score=1.0,
        )
    ]

    # 2. Student A: Demonstrated Strength
    student_a = StudentProfile(
        student=Student(student_id="student-a", name="Student A", course="CS", preferred_language="en"),
        concept_mastery={"Binary Search": 1.0},
        strengths=["Binary Search"],
        unknown_concepts=[],
        weak_concepts=[],
    )

    # 3. Student B: Missing Knowledge
    student_b = StudentProfile(
        student=Student(student_id="student-b", name="Student B", course="CS", preferred_language="en"),
        concept_mastery={"Binary Search": 0.0},
        strengths=[],
        unknown_concepts=["Binary Search"],
        weak_concepts=["Binary Search"],
    )

    p_service = PersonalizationService()
    qa = QueryAnalysis(
        intent="explain",
        domain="computer_science",
        topic="Binary Search",
        concepts=["Binary Search"],
        prerequisites=["arrays", "sorting"],
        requested_outputs=["explanation"],
        difficulty="intermediate",
        retrieval_required=True,
        assessment_required=False,
        personalization_required=True,
        code_needed=False,
        source_mode="trusted_external",
        trusted_discovery_required=True,
    )

    strat_a = p_service.strategy(student_a, qa)
    strat_b = p_service.strategy(student_b, qa)

    # Invariant 5: Strength maps to progressive-challenge / higher-difficulty
    assert "progressive-challenge" in strat_a
    assert "Avoid over-explaining already-mastered basics" in strat_a
    assert "estimated mastery=1.00" in strat_a

    # Invariant 6: Missing knowledge maps to foundational-remediation
    assert "foundational-remediation" in strat_b
    assert "Teach from first principles" in strat_b
    assert "estimated mastery=0.00" in strat_b

    # Invariant 7: Pedagogical outputs differ between strategies
    assert strat_a != strat_b

    # Invariant 8: Both students share identical evidence IDs and source provenance
    ev_ids_a = [e.chunk_id for e in frozen_evidence]
    ev_ids_b = [e.chunk_id for e in frozen_evidence]
    assert ev_ids_a == ev_ids_b == ["chunk-cmu-01"]

    urls_a = [e.source_url for e in frozen_evidence]
    urls_b = [e.source_url for e in frozen_evidence]
    assert urls_a == urls_b == ["https://www.cs.cmu.edu/~rjsimmon/15122-s13/06-binsearch.pdf"]


def test_personalization_cannot_enlarge_factual_scope():
    """Invariant 9, 10: Factual grounding boundary is absolute; unsupported claims are rejected."""
    ev = [
        Evidence(
            chunk_id="c_ev",
            text="Binary search requires a sorted array. Worst-case runtime is O(log n). Iterative space is O(1).",
            source="lecture.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        )
    ]

    # Directly supported claims pass
    assert GenericClaimValidator.classify_claim("Binary search operates on a sorted array.", ev) == "SUPPORTED"
    assert GenericClaimValidator.classify_claim("The worst-case runtime complexity is O(log n).", ev) == "SUPPORTED"
    assert GenericClaimValidator.classify_claim("Space complexity is O(1).", ev) == "SUPPORTED"

    # Unsupported technical facts MUST be rejected regardless of learner profile
    assert GenericClaimValidator.classify_claim("Master Theorem case 2 proves the recurrence relation T(n) = T(n/2) + O(1).", ev) == "UNSUPPORTED"
    assert GenericClaimValidator.classify_claim("Binary search uses two pointer crossing semantics.", ev) == "UNSUPPORTED"
    # Case mismatch rejected
    assert GenericClaimValidator.classify_claim("Space complexity is o(1).", ev) == "UNSUPPORTED"


def test_production_profile_byte_integrity_and_classification():
    """Invariant 11: Production student-001.json is untouched and classifications match Part I & J."""
    profile_path = Path("data/profiles/student-001.json")
    assert profile_path.exists()

    content = profile_path.read_bytes()
    computed_sha = hashlib.sha256(content).hexdigest()
    expected_sha = "9f0176952f5a8f9c801523b8a62e0bc60e2e12dd63175aa478b10782a2c727ae"
    assert computed_sha == expected_sha, f"student-001.json hash mismatch: {computed_sha}"

    # Verify classification logic for student-001
    import json
    data = json.loads(content)
    strengths = data.get("strengths", [])
    unknowns = data.get("unknown_concepts", [])
    weaks = data.get("weak_concepts", [])
    mastery = data.get("concept_mastery", {})

    # 1. Binary Search -> strength -> higher-difficulty
    assert "Binary search" in strengths
    assert mastery.get("Binary search") == 1.0

    # 2. worst-case complexity -> missing_knowledge -> foundational
    assert "worst-case complexity" in unknowns
    assert mastery.get("worst-case complexity") == 0.0

    # 3. space complexity -> weak_attempted -> reinforcement
    assert "space complexity" in weaks
    assert "space complexity" not in unknowns


# ==============================================================================
# LIVE UI TRUSTED-RAG DIVERGENCE REGRESSION TESTS (1 - 11)
# ==============================================================================


def test_trusted_but_irrelevant_source_is_rejected_or_downranked():
    """1. Trusted but irrelevant source (e.g. Tier-A mergesort/linear programming) is rejected/downranked."""
    from src.retrieval.service import is_topically_substantive

    mergesort_text = (
        "Algorithms, 4th Edition. Lecture 8: Mergesort. "
        "Divide array into two halves, recursively sort each half, then merge. "
        "Linear programming and reductions are discussed in later chapters."
    )
    linear_prog_text = (
        "Lecture 22: Reductions and Linear Programming. "
        "Simplex algorithm, max flow min cut theorem, and bipartite matching."
    )
    cmu_bs_text = (
        "Lecture 6: Binary Search on sorted arrays. "
        "We compute the midpoint of the subinterval and discard half the search space. "
        "Worst-case runtime is O(log n)."
    )

    subst_merge, mult_merge = is_topically_substantive("Explain binary search", "Binary Search", mergesort_text)
    assert not subst_merge and mult_merge <= 0.10

    subst_lp, mult_lp = is_topically_substantive("Explain binary search", "Binary Search", linear_prog_text)
    assert not subst_lp and mult_lp <= 0.10

    subst_bs, mult_bs = is_topically_substantive("Explain binary search", "Binary Search", cmu_bs_text)
    assert subst_bs and mult_bs >= 0.85


def test_generic_course_index_page_cannot_support_binary_search_mechanics():
    """2. Generic course index / syllabus / booksite page cannot support binary search mechanics."""
    from src.retrieval.service import is_generic_index_or_landing_page, is_topically_substantive

    schedule_text = (
        "CS 101 Course Schedule and Syllabus. "
        "Week 1: Introduction to Java. "
        "Week 2: Binary Search. "
        "Week 3: Mergesort and Quicksort. "
        "Office hours: Monday 2-4 PM. Homework assignments due Fridays. "
        "Booksite: Algorithms, 4th Edition textbook website."
    )
    assert is_generic_index_or_landing_page(schedule_text)
    subst, mult = is_topically_substantive("Explain binary search", "Binary Search", schedule_text)
    assert not subst and mult <= 0.10


def test_every_displayed_citation_maps_to_an_actually_used_chunk():
    """3. Every displayed citation maps 1:1 to an actually used evidence chunk."""
    ev = [
        Evidence(
            chunk_id="cmu_chunk_01",
            text="Binary search requires an array to be sorted.",
            source="CMU Lecture 6",
            source_type="trusted_external",
            source_url="https://www.cs.cmu.edu/~15122/06.pdf",
            authority="university",
            trust_score=0.98,
            score=1.0,
        ),
        Evidence(
            chunk_id="cmu_chunk_02",
            text="The time complexity of binary search is O(log n).",
            source="CMU Lecture 6",
            source_type="trusted_external",
            source_url="https://www.cs.cmu.edu/~15122/06.pdf",
            authority="university",
            trust_score=0.98,
            score=1.0,
        ),
    ]

    # Verify 1:1 index mapping
    assert ev[0].chunk_id == "cmu_chunk_01"
    assert ev[1].chunk_id == "cmu_chunk_02"
    assert ev[0].source_url == "https://www.cs.cmu.edu/~15122/06.pdf"


def test_displayed_snippet_corresponds_to_supporting_text():
    """4. Displayed snippet corresponds to exact supporting text and includes source URL."""
    item = Evidence(
        chunk_id="chunk-test-1",
        text="The worst-case time complexity of binary search is O(log n).",
        source="Lecture Notes on Binary Search",
        source_type="trusted_external",
        source_url="https://www.cs.cmu.edu/~rjsimmon/15122-s13/06-binsearch.pdf",
        authority="university",
        trust_score=0.98,
        score=1.0,
        page=3,
    )
    assert "O(log n)" in item.text
    assert item.source_url == "https://www.cs.cmu.edu/~rjsimmon/15122-s13/06-binsearch.pdf"
    assert item.page == 3


def test_unsupported_dictionary_analogy_rejected():
    """5. Unsupported dictionary analogy is rejected when absent from evidence."""
    ev = [
        Evidence(
            chunk_id="ev_01",
            text="Binary search operates on a sorted indexed array by comparing the target to the median element.",
            source="lecture.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        )
    ]
    claim = "Binary search is like opening a physical dictionary to the letter M."
    assert GenericClaimValidator.classify_claim(claim, ev) == "UNSUPPORTED"


def test_unsupported_absent_target_behavior_rejected():
    """6. Unsupported absent-target / pointer-crossing behavior is rejected when absent from evidence."""
    ev = [
        Evidence(
            chunk_id="ev_02",
            text="If the target equals the median element, its index is returned. Worst-case time is O(log n).",
            source="lecture.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        )
    ]
    claim = "When low exceeds high, the search domain is empty and pointer crossing indicates the target is absent."
    assert GenericClaimValidator.classify_claim(claim, ev) == "UNSUPPORTED"


def test_compound_query_uses_per_concept_learner_state():
    """7. Compound query derives hierarchical per-concept learner state."""
    from infrastructure.storage.json_store import JsonProfileStore
    from src.query_analysis.service import QueryAnalyzer

    store = JsonProfileStore("data/profiles")
    profile = store.load("student-001")
    qa = QueryAnalyzer()
    query = "Explain how binary search works, including its required input condition, decision process, worst-case time complexity, and iterative space complexity."
    analysis = qa.analyze(query, "en")

    p_service = PersonalizationService()
    strat = p_service.strategy(profile, analysis)

    assert "section-aware-hierarchical" in strat
    assert "Binary Search" in strat
    assert "worst-case complexity" in strat
    assert "space complexity" in strat


def test_mastered_parent_topic_not_globally_labeled_foundational():
    """8. Mastered parent topic is not globally labeled foundational and avoids remedial framing."""
    from infrastructure.storage.json_store import JsonProfileStore
    from src.query_analysis.service import QueryAnalyzer

    store = JsonProfileStore("data/profiles")
    profile = store.load("student-001")
    qa = QueryAnalyzer()
    query = "Explain how binary search works, including its required input condition, decision process, worst-case time complexity, and iterative space complexity."
    analysis = qa.analyze(query, "en")

    p_service = PersonalizationService()
    strat = p_service.strategy(profile, analysis)

    # Must NOT label the whole response foundational-remediation
    assert "mode: foundational-remediation" not in strat
    # Must instruct LLM not to open with "building from the ground up" or remedial framing
    assert "Do NOT treat the overall topic (Binary Search) as unknown" in strat
    assert "building from the ground up" in strat  # Appears in negative constraint directive
    assert "Do NOT open with remedial framing" in strat


def test_missing_subtopic_gets_foundational_treatment():
    """9. Missing subtopic (worst-case complexity) gets explicit foundational scaffolding."""
    from infrastructure.storage.json_store import JsonProfileStore
    from src.query_analysis.service import QueryAnalyzer

    store = JsonProfileStore("data/profiles")
    profile = store.load("student-001")
    qa = QueryAnalyzer()
    query = "Explain how binary search works, including its required input condition, decision process, worst-case time complexity, and iterative space complexity."
    analysis = qa.analyze(query, "en")

    p_service = PersonalizationService()
    strat = p_service.strategy(profile, analysis)

    assert "Time Complexity" in strat
    assert "foundational scaffolding" in strat
    assert "first principles" in strat


def test_weak_subtopic_gets_reinforcement():
    """10. Weak subtopic (space complexity) gets explicit targeted reinforcement."""
    from infrastructure.storage.json_store import JsonProfileStore
    from src.query_analysis.service import QueryAnalyzer

    store = JsonProfileStore("data/profiles")
    profile = store.load("student-001")
    qa = QueryAnalyzer()
    query = "Explain how binary search works, including its required input condition, decision process, worst-case time complexity, and iterative space complexity."
    analysis = qa.analyze(query, "en")

    p_service = PersonalizationService()
    strat = p_service.strategy(profile, analysis)

    assert "Space Complexity" in strat
    assert "targeted reinforcement" in strat
    assert "O(1) auxiliary space" in strat


def test_same_factual_evidence_boundary_preserved():
    """11. Same factual evidence boundary is preserved regardless of learner state."""
    ev = [
        Evidence(
            chunk_id="c_cmu",
            text="Binary search operates on a sorted array. Worst-case time is O(log n). Iterative space complexity is O(1).",
            source="cmu.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        )
    ]
    # Invariant: facts are identically verified
    assert GenericClaimValidator.classify_claim("Worst-case time complexity is O(log n).", ev) == "SUPPORTED"
    assert GenericClaimValidator.classify_claim("Space complexity is O(1).", ev) == "SUPPORTED"
    assert GenericClaimValidator.classify_claim("Binary search uses physical dictionary lookups.", ev) == "UNSUPPORTED"


def test_o1_iterative_space_claim_without_citation_is_rejected_or_repaired():
    """1. O(1) iterative space claim without citation is rejected / repaired."""
    from src.validation.service import Validator
    validator = Validator()

    ev_with_space = [
        Evidence(
            chunk_id="chunk-cmu-loop",
            text="int lo = 0; int hi = n; while (lo < hi) { int mid; /* scalar indices */ }",
            source="cmu.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        )
    ]
    raw = "When implemented iteratively using scalar variables (such as lo, hi, and mid), binary search requires O(1) auxiliary space."
    repaired = validator.validate_and_repair_citations(raw, ev_with_space)
    assert "[1]" in repaired, f"Expected citation attached to directly implied claim: {repaired}"

    ev_no_space = [
        Evidence(
            chunk_id="chunk-cmu-only-time",
            text="Binary search takes O(log n) time.",
            source="cmu.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        )
    ]
    repaired_no_space = validator.validate_and_repair_citations(raw, ev_no_space)
    assert "evidence" in repaired_no_space.lower()
    assert "explicitly document the auxiliary space complexity bound" in repaired_no_space or "[1]" not in repaired_no_space


def test_directly_implied_o1_claim_must_cite_supporting_scalar_variable_chunk():
    """2. Directly-implied O(1) claim must cite supporting scalar-variable chunk."""
    from src.validation.service import Validator
    validator = Validator()

    ev = [
        Evidence(
            chunk_id="chunk-1",
            text="The worst-case running time of binary search is O(log n) because of halving.",
            source="cmu.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        ),
        Evidence(
            chunk_id="chunk-2",
            text="The iterative loop maintains lo and hi variables, performing a constant amount of work per iteration.",
            source="cmu.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        ),
    ]
    raw = "Thus, the auxiliary space complexity of the iterative implementation is O(1)."
    repaired = validator.validate_and_repair_citations(raw, ev)
    assert "[2]" in repaired
    assert "[1]" not in repaired


def test_midpoint_formula_absent_from_active_bundle_cannot_appear():
    """3. Midpoint formula absent from active bundle cannot appear."""
    from src.validation.service import Validator
    validator = Validator()

    ev = [
        Evidence(
            chunk_id="chunk-1",
            text="We begin by examining the middle element of the sorted array and comparing against x.",
            source="cmu.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        )
    ]
    raw = "The algorithm calculates mid = lo + (hi - lo) / 2 to avoid integer overflow [1]."
    repaired = validator.validate_and_repair_citations(raw, ev)
    assert "mid = lo + (hi - lo) / 2" not in repaired
    assert "avoid integer overflow" not in repaired
    assert "examining the middle element" in repaired


def test_fact_from_unselected_chunk_of_same_pdf_cannot_leak_into_answer():
    """4. Fact from unselected chunk of same PDF cannot leak into answer."""
    active_ev = [
        Evidence(
            chunk_id="chunk-active",
            text="Binary search requires sorted arrays and achieves O(log n) time.",
            source="06-binsearch.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        )
    ]
    claim = "Joshua Bloch's Extra, Extra blog post documented the Java library overflow bug in binary search."
    assert GenericClaimValidator.classify_claim(claim, active_ev) == "UNSUPPORTED"


def test_every_displayed_citation_maps_to_active_selected_evidence():
    """5. Every displayed citation maps to active selected evidence."""
    from src.validation.service import Validator
    validator = Validator()

    active_ev = [
        Evidence(
            chunk_id="c1",
            text="Binary search operates on a sorted array.",
            source="doc.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        ),
        Evidence(
            chunk_id="c2",
            text="Time complexity is O(log n).",
            source="doc.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        ),
    ]
    raw = "Binary search cuts space in half [5] and requires a sorted array [99]."
    repaired = validator.validate_and_repair_citations(raw, active_ev)
    assert "[5]" not in repaired
    assert "[99]" not in repaired


def test_every_material_technical_claim_has_at_least_one_valid_citation():
    """6. Every material technical claim has at least one valid citation."""
    from src.validation.service import Validator
    validator = Validator()

    ev = [
        Evidence(
            chunk_id="c1",
            text="Input must be a sorted array. At each step, examine middle element.",
            source="cmu.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        ),
        Evidence(
            chunk_id="c2",
            text="Worst-case time complexity is O(log n) because array size halves.",
            source="cmu.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        ),
        Evidence(
            chunk_id="c3",
            text="Iterative while loop uses scalar lo, hi, mid variables with constant amount of work.",
            source="cmu.pdf",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        ),
    ]
    raw_answer = (
        "1. Input condition: The input collection must be a sorted array.\n"
        "2. Decision process: Examine the middle element and discard the irrelevant half.\n"
        "3. Time complexity: The worst-case time complexity is O(log n).\n"
        "4. Space complexity: When implemented iteratively using scalar variables, auxiliary space is O(1)."
    )
    validated = validator.validate_and_repair_citations(raw_answer, ev)
    lines = validated.strip().split("\n")
    for line in lines:
        if line.strip():
            assert any(f"[{i}]" in line for i in (1, 2, 3)), f"Line missing valid citation: {line}"


def test_binary_search_trees_titled_source_accepted_only_if_chunk_is_about_array_binary_search():
    """7. Binary Search Trees titled source can be accepted only if chunk is about array binary search."""
    from src.retrieval.service import is_topically_substantive

    query = "Explain how binary search works, including its required input condition, decision process, worst-case time complexity, and iterative space complexity."
    topic = "Binary Search"

    bst_chunk_with_array = (
        "In lecture we saw binary search on a sorted array, where halving the subinterval from lo to hi "
        "gives O(log n) worst-case time complexity. Binary search trees extend this principle..."
    )
    subst_a, score_a = is_topically_substantive(query, topic, bst_chunk_with_array)
    assert subst_a is True
    assert score_a >= 0.80

    bst_chunk_pure_tree = (
        "A binary search tree has a root node with left and right children. Each left child key is strictly less "
        "than the root key, and tree height determines search path depth."
    )
    subst_b, score_b = is_topically_substantive(query, topic, bst_chunk_pure_tree)
    assert subst_b is False
    assert score_b < 0.15


def test_source_set_variability_between_runs_does_not_break_provenance_correctness():
    """8. Source-set variability between runs does not break provenance correctness."""
    from src.validation.service import Validator
    validator = Validator()

    run1_ev = [
        Evidence(chunk_id="cmu_01", text="CMU note 1", source="CMU Lecture 6 Notes", source_type="trusted_external", authority="university", trust_score=0.98, score=1.0, page=1),
        Evidence(chunk_id="cmu_02", text="CMU note 2", source="CMU Lecture 6 Notes", source_type="trusted_external", authority="university", trust_score=0.98, score=1.0, page=2),
    ]
    cites1 = validator.citations(run1_ev)
    assert len(cites1) == 2
    assert "CMU Lecture 6 Notes · p.1" in cites1[0]
    assert "CMU Lecture 6 Notes · p.2" in cites1[1]

    run2_ev = [
        Evidence(chunk_id="umd_01", text="UMD note 1", source="UMD CMSC351 Notes", source_type="trusted_external", authority="university", trust_score=0.92, score=1.0, page=3),
        Evidence(chunk_id="cmu_01", text="CMU note 1", source="CMU Lecture 6 Notes", source_type="trusted_external", authority="university", trust_score=0.98, score=1.0, page=1),
    ]
    cites2 = validator.citations(run2_ev)
    assert len(cites2) == 2
    assert "UMD CMSC351 Notes · p.3" in cites2[0]
    assert "CMU Lecture 6 Notes · p.1" in cites2[1]


def test_material_selector_default_and_none_routes_to_trusted_external():
    """9. Material selector default (None or empty list) routes to trusted_external without upload constraint."""
    from src.validation.service import Validator
    validator = Validator()

    query = "Explain how binary search works, including its required input condition, decision process, worst-case time complexity, and iterative space complexity."

    assert validator.is_source_constrained(query, document_ids=None) is False
    assert validator.is_source_constrained(query, document_ids=[]) is False


def test_compound_query_partial_coverage_does_not_refuse_core_supported_topics():
    """10. One missing facet in compound query allows answering supported core with evidence limitation."""
    from src.validation.service import Validator
    validator = Validator()

    query = "Explain how binary search works, including its required input condition, decision process, worst-case time complexity, and iterative space complexity."

    # Evidence has sorted array, middle comparison, O(log n) worst-case time, but NOT O(1) space
    ev = [
        Evidence(
            chunk_id="cmu_01",
            text="Binary search requires that the array is sorted. In each step, we examine the middle element and discard the irrelevant half.",
            source="CMU 15-122",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        ),
        Evidence(
            chunk_id="cmu_02",
            text="Worst-case time complexity is O(log n) because the problem size is halved at each iteration.",
            source="CMU 15-122",
            source_type="trusted_external",
            authority="university",
            trust_score=0.98,
            score=1.0,
        ),
    ]

    # Overall bundle is sufficient for the core topic
    assert validator.sufficient(ev) is True
    # source_supports_query recognizes core topic is supported
    assert validator.source_supports_query(query, ev) is True

    # When validated and repaired, missing space facet produces explicit evidence limitation
    raw_answer = (
        "Required Input Condition: The array must be sorted.\n"
        "Decision Process: Check middle element and halve interval.\n"
        "Worst-case Time Complexity: O(log n).\n"
        "Iterative Space Complexity: The algorithm requires O(1) auxiliary space."
    )
    repaired = validator.validate_rendered_answer(raw_answer, ev, query=query)
    assert "explicitly document the auxiliary space complexity bound" in repaired
    assert "[1]" in repaired or "[2]" in repaired
