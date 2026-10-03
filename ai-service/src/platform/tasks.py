"""
Platform AI tasks: the single place where the GenAI platform backend runs its
structured AI work through LeRna (question generation, answer evaluation,
grading, remedial content, study-tool resources, topic detection...).

Every task returns one JSON object. LeRna owns:
  - provider selection and runtime failover across the configured LLM pool,
  - JSON extraction / repair of the model output,
  - the output contract check (required keys per task),
  - the prompts of the tasks it defines itself (topic detection).

For the platform's assessment/content tasks the backend sends the task
contract (instructions + input); LeRna executes it with its provider pool and
validates the result shape. The backend validates the final schema again and
keeps an identical local path, so a LeRna outage never breaks a feature.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from src.core.exceptions import ProviderError
from src.platform.sanad_prompts import (
    SANAD_ADAPT_PROMPT,
    SANAD_LESSON_PROMPT,
    SANAD_PLAN_PROMPT,
    SANAD_UNDERSTAND_PROMPT,
)

LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic", "fr": "French", "sw": "Swahili", "ha": "Hausa",
    "am": "Amharic", "so": "Somali", "yo": "Yoruba", "ig": "Igbo", "zu": "Zulu",
}

# ---------------------------------------------------------------- prompts
EXTRACT_TOPICS_PROMPT = (
    "You organise university course material into study topics. You receive the "
    "course title, the topics the course already has, and numbered sections of ONE "
    "uploaded file. Identify the distinct teachable topics the file covers (usually "
    "1-8; a short file may have one). A topic is a unit a student can be strong or "
    "weak in (e.g. 'Deadlocks', 'CPU Scheduling', 'Binary Search Trees') - never a "
    "whole course name, a chapter number, or a single fact.\n"
    "Rules:\n"
    "- If a topic is the same subject as an existing course topic, reuse it by "
    "returning its existingTopicId (do not create a near-duplicate such as "
    "'Deadlock' vs 'Deadlocks').\n"
    "- New topic titles: 2-6 words, Title Case, in English (standard academic "
    "naming), even if the file is in another language.\n"
    "- summary: one sentence (max 30 words) describing what the topic covers in this course.\n"
    "- sectionIds: the section numbers that belong to the topic; every section should "
    "belong to at least one topic when it has academic content.\n"
    "- Ignore administrative text (grading policy, office hours, dates).\n"
    'Return JSON only: {"topics":[{"title":string,"existingTopicId":string|null,'
    '"summary":string,"sectionIds":[number]}]}'
)

CLASSIFY_TOPIC_PROMPT = (
    "You map a student's learning activity (a question, a requested practice subject, "
    "or an assessment question) to ONE topic of a course. You receive the text and the "
    "course topics (id, title, summary). Choose the topic the text is mainly about. "
    "If the text is not about any listed topic (off-course, greeting, too vague), "
    "return null. Do not guess: confidence below 0.5 means null.\n"
    'Return JSON only: {"topicId":string|null,"confidence":number}'
)

# task -> (LeRna-owned system prompt or None, required output keys)
TASKS: dict[str, tuple[str | None, tuple[str, ...]]] = {
    "extract_topics": (EXTRACT_TOPICS_PROMPT, ("topics",)),
    "classify_topic": (CLASSIFY_TOPIC_PROMPT, ("topicId",)),
    "generate_diagnostic_questions": (None, ()),
    "generate_practice_questions": (None, ()),
    "generate_reassessment_questions": (None, ()),
    "evaluate_answer": (None, ()),
    "grade_assignment_answer": (None, ()),
    "generate_remedial_content": (None, ()),
    "answer_tutor_question": (None, ()),
    "answer_tutor_question_external": (None, ()),
    "plan_trusted_source_discovery": (None, ()),
    "deck_outline": (None, ()),
    "diagram_spec": (None, ()),
    # Sanad study agent (LeRna-owned prompts)
    "sanad_understand": (SANAD_UNDERSTAND_PROMPT, ("intent", "reply")),
    "sanad_plan": (SANAD_PLAN_PROMPT, ("summary", "days")),
    "sanad_adapt": (SANAD_ADAPT_PROMPT, ("message", "days")),
    "sanad_lesson": (SANAD_LESSON_PROMPT, ("explanation",)),
}
GENERATE_RESOURCE = re.compile(r"^generate_[a-z_]{2,40}$")


class TaskError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def is_known_task(task: str) -> bool:
    return task in TASKS or bool(GENERATE_RESOURCE.match(task or ""))


def extract_json(text: str) -> Any:
    raw = re.sub(r"<think>[\s\S]*?</think>", "", text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except Exception:
            pass
    raise TaskError("The model did not return valid JSON")


# provider name -> monotonic time until which it is skipped after a failure
_COOLDOWN: dict[str, float] = {}
COOLDOWN_SECONDS = 60


def run_task(ai, task: str, system: str | None, payload: Any, language: str | None = None) -> dict:
    if not is_known_task(task):
        raise TaskError(f"Unknown task '{task}'", status=400)
    owned, required = TASKS.get(task, (None, ()))
    instructions = owned or (system or "").strip()
    if not instructions:
        raise TaskError(f"Task '{task}' needs instructions", status=400)
    if language and language in LANGUAGE_NAMES and owned is None and task != "classify_topic":
        # The platform prompt already states the language; this only reinforces it.
        instructions += f"\nWrite every student-facing text in {LANGUAGE_NAMES[language]}."
    instructions += "\nRespond with a single JSON object and nothing else."
    user = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)

    llms = getattr(getattr(ai, "tutor", None), "llms", None) or {}
    now = time.monotonic()
    candidates = [(n, p) for n, p in llms.items() if n != "unconfigured" and _COOLDOWN.get(n, 0) <= now]
    if not candidates:
        raise TaskError("No healthy configured LLM provider is currently available.", status=503)

    last_error: Exception | None = None
    for name, provider in candidates:
        for attempt in range(2):
            try:
                text = provider.generate_prompt(instructions, user)
                output = extract_json(text)
                if not isinstance(output, dict):
                    raise TaskError("The model output is not a JSON object")
                missing = [key for key in required if key not in output]
                if missing:
                    raise TaskError(f"The model output misses {', '.join(missing)}")
                return {
                    "task": task,
                    "output": output,
                    "provider": getattr(provider, "provider", name),
                    "model": getattr(provider, "model", "unknown"),
                }
            except TaskError as exc:  # bad output: one retry on the same provider
                last_error = exc
                continue
            except (ProviderError, Exception) as exc:  # provider down / quota
                last_error = exc
                _COOLDOWN[name] = time.monotonic() + COOLDOWN_SECONDS
                break
    raise TaskError(f"All providers failed for '{task}': {last_error}", status=503)
