from __future__ import annotations

import datetime
from typing import Any
from pydantic import BaseModel, Field

# Explicit domain / curriculum prerequisite relationships: prerequisite -> target
EXPLICIT_PREREQUISITES: dict[str, str] = {
    "neural networks": "convolution",
    "matrices": "convolution",
    "embeddings": "retrieval",
    "variables": "functions",
    "control flow": "functions",
    "sorting": "binary search",
    "arrays": "binary search",
}


class NextLearningAction(BaseModel):
    action: str
    reason: str
    target_concepts: list[str]
    strategy: str
    recommended_resources: list[str]
    priority: str = "medium"
    triggering_evidence: str | None = None


def is_proven_prerequisite(concept: str, profile: Any) -> bool:
    """
    A prerequisite gap is proven ONLY when:
    1. An explicit prerequisite relationship exists (prerequisite A -> target B).
    2. Prerequisite A has insufficient mastery (< 0.70) while target B is active / being learned.
    Low mastery alone MUST NOT automatically mean prerequisite gap.
    """
    if not concept or not isinstance(concept, str):
        return False
    c_norm = concept.strip().lower()
    mastery = getattr(profile, "concept_mastery", {}) or {}

    # 1. Check explicit profile prerequisite graph / dependencies if stored
    graph = (
        getattr(profile, "prerequisite_graph", {})
        or getattr(profile, "prerequisite_dependencies", {})
        or {}
    )
    if concept in graph or c_norm in graph:
        val = mastery.get(concept, mastery.get(c_norm, 0.0))
        return float(val) < 0.70

    # 2. Check explicit assessment question prerequisite concepts from history
    for record in getattr(profile, "assessment_history", []):
        for q_prereq in record.get("prerequisite_concepts", []):
            if q_prereq and str(q_prereq).strip().lower() == c_norm:
                val = mastery.get(concept, 0.0)
                return float(val) < 0.70

    # 3. Check canonical curriculum prerequisites
    if c_norm in EXPLICIT_PREREQUISITES:
        val = mastery.get(concept, mastery.get(c_norm, 0.0))
        return float(val) < 0.70

    return False


class LearningOrchestrator:
    """
    Deterministic personalization decision system.
    Evaluates learner state according to explicit priority ordering:
    1. Confirmed Misconceptions (Priority A) -> correct_misconception
    2. Proven Prerequisite Gaps (Priority B) -> remediate_prerequisite
    3. Missing Knowledge (Priority C)        -> build_foundation
    4. Weak Attempted Concepts (Priority D)  -> targeted_remediation
    5. Scheduled Spaced Review (Priority E)  -> spaced_review
    6. Mastered / No Active Gaps (Priority F) -> progress
    """

    def _is_proven_prerequisite(self, concept: str, profile: Any) -> bool:
        return is_proven_prerequisite(concept, profile)

    def next_action(self, profile: Any) -> NextLearningAction:
        mastery = getattr(profile, "concept_mastery", {}) or {}

        # Priority A: Confirmed Misconception
        misconceptions = getattr(profile, "misconceptions", []) or []
        if misconceptions:
            targets = [
                c
                for c in getattr(profile, "weak_concepts", [])
                if any(c.lower() in m.lower() for m in misconceptions)
            ] or [misconceptions[0][:40]]
            return NextLearningAction(
                action="correct_misconception",
                reason="A confirmed misconception was detected in learning evidence.",
                target_concepts=targets[:2],
                strategy="misconception-correction",
                recommended_resources=["explanation", "comparison", "quiz"],
                priority="high",
                triggering_evidence=f"Active misconception: {misconceptions[0]}",
            )

        # Priority B: Proven Prerequisite Gap
        raw_prereqs = getattr(profile, "prerequisite_gaps", []) or []
        proven_prereqs = [
            c for c in raw_prereqs if self._is_proven_prerequisite(c, profile)
        ]
        if proven_prereqs:
            return NextLearningAction(
                action="remediate_prerequisite",
                reason="A proven foundational prerequisite gap is blocking progress.",
                target_concepts=proven_prereqs[:2],
                strategy="prerequisite",
                recommended_resources=["explanation", "diagram", "practice"],
                priority="high",
                triggering_evidence=f"Prerequisite relationship exists and mastery is below 70%: {proven_prereqs[0]}",
            )

        # Priority C: Missing Knowledge (Student explicitly selected "I don't know")
        unknown_concepts = list(getattr(profile, "unknown_concepts", []))
        if not unknown_concepts and getattr(profile, "assessment_history", None):
            unknown_concepts = list(
                profile.assessment_history[-1].get("unknown_concepts", [])
            )

        active_missing = [
            c for c in unknown_concepts if float(mastery.get(c, 0.0)) < 0.70
        ]
        if active_missing:
            return NextLearningAction(
                action="build_foundation",
                reason="Missing knowledge was identified from assessment evidence; foundational learning is required.",
                target_concepts=active_missing[:2],
                strategy="foundational",
                recommended_resources=["explanation", "diagram", "study_guide"],
                priority="high",
                triggering_evidence=f"Explicit 'I don't know' recorded for: {active_missing[0]}",
            )

        # Priority D: Weak Attempted Concept
        weak_concepts = getattr(profile, "weak_concepts", []) or []
        weak_attempted = [
            c
            for c in weak_concepts
            if c not in active_missing and float(mastery.get(c, 0.0)) < 0.70
        ]
        if weak_attempted:
            vals = [float(mastery.get(x, 0.0)) for x in weak_attempted]
            is_severe = vals and min(vals) < 0.40
            return NextLearningAction(
                action="targeted_remediation",
                reason="These concepts were attempted but need reinforcement to reach mastery threshold.",
                target_concepts=weak_attempted[:2],
                strategy="simple-step-by-step" if is_severe else "practice",
                recommended_resources=(
                    ["explanation", "diagram", "flashcards"]
                    if is_severe
                    else ["practice", "quiz"]
                ),
                priority="medium",
                triggering_evidence=f"Mastery below 70% on attempted concept: {weak_attempted[0]} ({mastery.get(weak_attempted[0], 0.0):.0%})",
            )

        # Priority E: Spaced Repetition Due Review
        now = datetime.datetime.now(datetime.timezone.utc)
        due_concepts = []
        for item in getattr(profile, "review_queue", []):
            try:
                due_dt = datetime.datetime.fromisoformat(item["due_date"])
                c_name = item.get("concept", "")
                if due_dt <= now and float(mastery.get(c_name, 0.0)) >= 0.70:
                    due_concepts.append(c_name)
            except Exception:
                pass
        if due_concepts:
            return NextLearningAction(
                action="spaced_review",
                reason="Scheduled spaced repetition review is due to maintain memory retention.",
                target_concepts=due_concepts[:2],
                strategy="review",
                recommended_resources=["flashcards", "active_recall"],
                priority="medium",
                triggering_evidence=f"Interval review due for: {due_concepts[0]}",
            )

        # Priority F: Advance to Next Concept
        recent = getattr(profile, "recent_topics", []) or []
        target = recent[-1:] or ["Advanced Topics"]
        return NextLearningAction(
            action="progress",
            reason="No blocking gaps are currently detected.",
            target_concepts=target,
            strategy="higher-difficulty",
            recommended_resources=["quiz", "study_guide"],
            priority="low",
            triggering_evidence="All current concepts have reached >= 70% mastery with no active misconceptions.",
        )
