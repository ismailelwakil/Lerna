"""Content Verification Service (spec #30) — rule checks always, model-based
fact-check (reasoning model) when sources exist. Never trusts raw output."""
from __future__ import annotations

from typing import Optional

from ...core.logging import get_logger
from ...core.security import new_id
from ...db import get_database
from ...db.models import ContentVerification
from ...providers.llm.openrouter import llm
from ...prompts.templates import verification_prompt
from pydantic import BaseModel

log = get_logger("verify")


class Verdict(BaseModel):
    supported: bool
    issues: list[str] = []
    severity: str = "none"


async def verify_text(content_text: str, source_text: str,
                      student_id: Optional[str] = None) -> tuple[bool, str]:
    """Model fact-check of content against its source."""
    if llm.mode == "mock":
        return True, "mock mode — skipped"
    system, task = verification_prompt(content_text, source_text)
    try:
        verdict = await llm.structured(
            [{"role": "system", "content": system}, {"role": "user", "content": task}],
            Verdict, student_id=student_id, request_type="verification",
            max_tokens=800)
        return verdict.supported, "; ".join(verdict.issues[:4]) or verdict.severity
    except Exception as exc:  # noqa: BLE001 — verification must not crash delivery
        log.warning("verify_failed_open", extra={"ctx": {"err": str(exc)[:160]}})
        return True, "verification unavailable"


def rule_checks(content_type: str, body: dict) -> list[str]:
    issues: list[str] = []
    if content_type in {"explanation", "summary", "notes", "study_guide", "example"}:
        text = str(body)
        if len(text) < 80:
            issues.append("too_short")
        if "http://" in text:
            issues.append("insecure_url_in_content")
    if content_type == "flashcards":
        cards = body.get("cards") or body.get("flashcards") or []
        if not cards:
            issues.append("no_cards")
        seen = set()
        for card in cards:
            front = str(card.get("front", "")).strip().lower()
            if not front:
                issues.append("empty_card_front")
            if front in seen:
                issues.append("duplicate_card")
            seen.add(front)
    return issues


def persist(content_item_id: str, checker: str, passed: bool, issues: list[str],
            detail: Optional[dict] = None) -> None:
    try:
        db = get_database()
        with db.session_scope() as session:
            session.add(ContentVerification(
                id=new_id(), content_item_id=content_item_id, checker=checker,
                passed=passed, issues=issues, detail=detail or {}))
    except Exception as exc:  # noqa: BLE001
        log.warning("verify_persist_failed", extra={"ctx": {"err": str(exc)[:120]}})


async def verify_content(*, content_item_id: str, content_type: str, body: dict,
                         source_text: str, student_id: Optional[str]) -> dict:
    issues = rule_checks(content_type, body)
    model_checked = False
    if source_text and content_type in {"explanation", "summary", "study_guide",
                                        "notes", "example"} and llm.mode != "mock":
        text = _body_text(body)
        ok, why = await verify_text(text[:6000], source_text[:6000], student_id)
        model_checked = True
        if not ok:
            issues.append(f"source_disagreement: {why}")
    passed = not [i for i in issues if not i.startswith("source_disagreement")] and not (
        [i for i in issues if i.startswith("source_disagreement")])
    result = {"passed": passed, "issues": issues, "checker":
              "rules+model" if model_checked else "rules"}
    persist(content_item_id, result["checker"], passed, issues,
            {"model_checked": model_checked})
    return result


def _body_text(body: dict) -> str:
    import json
    try:
        return body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(body)