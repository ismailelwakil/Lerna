from __future__ import annotations

import datetime
from typing import Any
from src.contracts.models import StudentProfile
from src.personalization.orchestrator import is_proven_prerequisite


class StudyPlannerService:
    """Generates reactive study plans tailored to student weaknesses, gaps, and goals."""

    def build_study_plan(self, profile: StudentProfile) -> list[dict[str, Any]]:
        plan: list[dict[str, Any]] = []

        # 1. Active Misconceptions (Priority A - High)
        for misc in getattr(profile, "misconceptions", []):
            plan.append({
                "title": "Resolve Misconception",
                "concept": misc[:40],
                "priority": "high",
                "reason": f"Active misconception: {misc}",
                "recommended_actions": [
                    "Ask Tutor to contrast the misconception with the correct concept",
                    "Generate a comparative analysis breakdown",
                    "Retake diagnostic quiz to verify correction",
                ],
                "completed": False,
            })

        # 2. Proven Prerequisite Gaps (Priority B - High)
        for prereq in getattr(profile, "prerequisite_gaps", []):
            if any(p["concept"] == prereq for p in plan):
                continue
            if not is_proven_prerequisite(prereq, profile):
                continue
            plan.append({
                "title": f"Remediate Prerequisite: {prereq}",
                "concept": prereq,
                "priority": "high",
                "reason": "Missing foundational prerequisite is blocking progress.",
                "recommended_actions": [
                    f"Ask Tutor for a step-by-step introduction to {prereq}",
                    f"Generate a Study Guide on {prereq}",
                    "Complete diagnostic assessment after review",
                ],
                "completed": False,
            })

        # 3. Missing Knowledge / Foundational Gaps (Priority C - High)
        unknown_concepts = list(getattr(profile, "unknown_concepts", []))
        if not unknown_concepts and getattr(profile, "assessment_history", None):
            for record in reversed(profile.assessment_history):
                for unk in record.get("unknown_concepts", []):
                    if unk not in unknown_concepts:
                        unknown_concepts.append(unk)
        for unk in unknown_concepts:
            if any(p["concept"] == unk for p in plan):
                continue
            mastery = float(profile.concept_mastery.get(unk, 0.0))
            if mastery < 0.70:
                plan.append({
                    "title": f"Build Foundation: {unk}",
                    "concept": unk,
                    "priority": "high",
                    "reason": "Missing knowledge was identified from assessment evidence; foundational learning is required.",
                    "recommended_actions": [
                        f"Ask Tutor for a step-by-step introduction to {unk}",
                        f"Generate a Study Guide on {unk}",
                        f"Complete a short check on {unk} once fundamentals are established",
                    ],
                    "completed": False,
                })

        # 4. Weak Attempted Concepts (Priority D - Medium)
        for weak in getattr(profile, "weak_concepts", []):
            if any(p["concept"] == weak for p in plan):
                continue
            mastery = profile.concept_mastery.get(weak, 0.0)
            if float(mastery) < 0.70:
                plan.append({
                    "title": f"Reinforce Weak Concept: {weak}",
                    "concept": weak,
                    "priority": "medium",
                    "reason": f"Current mastery is {mastery:.0%}, below target threshold of 70%.",
                    "recommended_actions": [
                        f"Generate Flashcards and practice quiz on {weak}",
                        f"Review worked examples with the Tutor",
                        "Complete practice problem set",
                    ],
                    "completed": False,
                })

        # 5. Spaced Repetition Due Reviews (Priority E - Medium)
        now = datetime.datetime.now(datetime.timezone.utc)
        for item in getattr(profile, "review_queue", []):
            try:
                due_dt = datetime.datetime.fromisoformat(item["due_date"])
                if due_dt <= now and not any(p["concept"] == item["concept"] for p in plan):
                    plan.append({
                        "title": f"Spaced Repetition Review: {item['concept']}",
                        "concept": item["concept"],
                        "priority": "medium",
                        "reason": f"Scheduled interval review is due (repetition {item.get('repetition', 0)}).",
                        "recommended_actions": [
                            f"Quick active recall on {item['concept']}",
                            "Self-assess memory retention",
                        ],
                        "completed": False,
                    })
            except Exception:
                pass

        # 6. Advancement for Strengths / Progress (Priority F - Low)
        if not plan:
            recent = profile.recent_topics[-1] if profile.recent_topics else "Advanced Topics"
            plan.append({
                "title": f"Advance Beyond Fundamentals: {recent}",
                "concept": recent,
                "priority": "low",
                "reason": "All fundamental gaps and misconceptions are resolved.",
                "recommended_actions": [
                    "Explore higher-difficulty applied scenarios",
                    "Generate an architecture diagram or code exercise",
                    "Take a comprehensive challenge exam",
                ],
                "completed": False,
            })

        profile.study_plan = plan
        return plan
