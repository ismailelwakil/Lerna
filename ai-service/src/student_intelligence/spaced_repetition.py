from __future__ import annotations

import datetime
from typing import Any
from src.contracts.models import StudentProfile


class SpacedRepetitionService:
    """Spaced repetition scheduler based on SM-2 and half-life intervals."""

    def __init__(self, default_ease_factor: float = 2.5):
        self.default_ease_factor = default_ease_factor

    def update_queue(self, profile: StudentProfile) -> list[dict[str, Any]]:
        now = datetime.datetime.now(datetime.timezone.utc)
        existing_items = {
            item["concept"]: dict(item)
            for item in getattr(profile, "review_queue", [])
            if "concept" in item
        }

        all_concepts = set(profile.concept_mastery.keys()) | set(profile.weak_concepts)

        for concept in all_concepts:
            mastery = float(profile.concept_mastery.get(concept, 0.0))
            is_weak = concept in profile.weak_concepts or mastery < 0.60

            if concept in existing_items:
                item = existing_items[concept]
                item["mastery"] = mastery
                # If newly marked weak and never reviewed, adjust due date sooner
                if is_weak and item.get("last_reviewed") is None and datetime.datetime.fromisoformat(item["due_date"]) > now:
                    item["due_date"] = now.isoformat()
                    item["interval_days"] = 1.0
            else:
                interval_days = 1.0 if is_weak else (2.0 if mastery < 0.80 else 4.0)
                due_date = now + datetime.timedelta(days=interval_days if not is_weak else 0)
                existing_items[concept] = {
                    "concept": concept,
                    "due_date": due_date.isoformat(),
                    "interval_days": interval_days,
                    "repetition": 0,
                    "ease_factor": self.default_ease_factor,
                    "last_reviewed": None,
                    "mastery": mastery,
                }

        # Sort queue by due date
        queue = sorted(
            existing_items.values(),
            key=lambda x: (x["due_date"], x["mastery"]),
        )
        profile.review_queue = queue
        return queue

    def record_review(
        self,
        profile: StudentProfile,
        concept: str,
        remembered: bool,
    ) -> dict[str, Any]:
        """
        Record a spaced repetition review event.
        STRICT ASSESSMENT-TRUTH SEPARATION:
        Remembered / Forgot mutates ONLY review scheduling metadata:
          - repetition count
          - interval days
          - ease factor
          - last reviewed timestamp
          - due date
          - last result
        Self-report MUST NEVER directly or indirectly modify assessment-grounded state:
          - concept_mastery
          - strengths
          - weak_concepts
          - unknown_concepts
          - misconceptions
          - prerequisite_gaps
          - assessment_history
          - assessment scores
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        queue = self.update_queue(profile)
        target_item = None

        for item in queue:
            if item["concept"] == concept:
                target_item = item
                break

        if target_item is None:
            target_item = {
                "concept": concept,
                "due_date": now.isoformat(),
                "interval_days": 1.0,
                "repetition": 0,
                "ease_factor": self.default_ease_factor,
                "last_reviewed": None,
                "mastery": float(profile.concept_mastery.get(concept, 0.0)),
            }
            queue.append(target_item)

        repetition = target_item.get("repetition", 0)
        ease = target_item.get("ease_factor", self.default_ease_factor)

        if remembered:
            repetition += 1
            if repetition == 1:
                interval = 1.0
            elif repetition == 2:
                interval = 3.0
            else:
                interval = round(target_item.get("interval_days", 3.0) * ease, 1)
            ease = max(1.3, ease + 0.1)
        else:
            repetition = 0
            interval = 1.0
            ease = max(1.3, ease - 0.2)

        target_item["repetition"] = repetition
        target_item["ease_factor"] = round(ease, 2)
        target_item["interval_days"] = interval
        target_item["last_reviewed"] = now.isoformat()
        target_item["due_date"] = (now + datetime.timedelta(days=interval)).isoformat()
        target_item["last_result"] = "remembered" if remembered else "forgot"
        target_item["mastery"] = float(profile.concept_mastery.get(concept, 0.0))

        profile.review_queue = sorted(queue, key=lambda x: (x["due_date"], x["mastery"]))
        return target_item

    def get_due_reviews(self, profile: StudentProfile) -> list[dict[str, Any]]:
        now = datetime.datetime.now(datetime.timezone.utc)
        queue = self.update_queue(profile)
        due = []
        for item in queue:
            try:
                due_dt = datetime.datetime.fromisoformat(item["due_date"])
                if due_dt <= now:
                    due.append(item)
            except Exception:
                due.append(item)
        return due
