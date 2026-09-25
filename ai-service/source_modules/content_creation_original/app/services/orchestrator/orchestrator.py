"""ContentOrchestrator (spec #5) — the single brain that decides what to
generate, which sources ground it, which provider serves it, verifies the
result, persists ContentItems, and tracks cost. Routes NEVER touch providers."""
from __future__ import annotations

from typing import Optional

from ...core.exceptions import (GenerationError, InsufficientSourceError,
                                NotFoundError)
from ...core.logging import get_logger
from ...core.security import new_id
from ...db import get_database
from ...db.models import ContentItem, UploadedDocument
from ...providers.llm.openrouter import llm
from ...prompts import templates
from ...schemas.common import BaseContentRequest
from ...services.personalization.service import learner_dict, next_strategy
from ...services.rag.rag_service import rag
from ...services.telemetry import telemetry

log = get_logger("orchestrator")


class Orchestrator:
    # ------------------------------------------------------------ sources
    async def gather_context(self, request: BaseContentRequest) -> tuple[str, list[dict]]:
        """Inline material + RAG over the student's documents → untrusted block
        + client-safe source refs. Enforces student isolation."""
        chunks = []
        if request.document_ids:
            db = get_database()
            with db.session_scope() as session:
                for document_id in request.document_ids:
                    doc = session.get(UploadedDocument, document_id)
                    if doc is None or doc.student_id != request.student_id:
                        raise NotFoundError("Document not found.")
            chunks = await rag.retrieve(
                request.student_id, f"{request.topic} {request.focus if hasattr(request, 'focus') else ''}".strip(),
                document_ids=request.document_ids, k=6)
        inline = request.inline_material or ""
        if inline and not chunks:
            from ...core.security import wrap_untrusted
            return wrap_untrusted(inline[:8000], label="source"), []
        if not chunks and not inline and not request.allow_external_knowledge:
            # no grounding available — will be flagged by callers that require it
            return "", []
        block = rag.context_block(chunks) if chunks else ""
        if inline:
            from ...core.security import wrap_untrusted
            block += ("\n\n" if block else "") + wrap_untrusted(inline[:8000], label="source")
        return block, [c.reference() for c in chunks]

    def owned_document(self, student_id: str, document_id: str) -> UploadedDocument:
        db = get_database()
        with db.session_scope() as session:
            doc = session.get(UploadedDocument, document_id)
            if doc is None or doc.student_id != student_id:
                raise NotFoundError("Document not found.")
            return doc

    # ------------------------------------------------------------ persist
    def persist(self, *, student_id: str, course_id: Optional[str], type_: str,
                topic: str, title: str, difficulty: str, level: str, body: dict,
                source_refs: list, source_ids: list, verified: bool,
                verification: dict) -> ContentItem:
        db = get_database()
        with db.session_scope() as session:
            item = ContentItem(
                id=new_id(), student_id=student_id, course_id=course_id, type=type_,
                topic=topic[:300], title=title[:300], difficulty=difficulty,
                student_level=level, body=body, source_refs=source_refs,
                source_ids=source_ids, verified=verified, verification=verification)
            session.add(item)
            return item

    @staticmethod
    def meta(item: ContentItem, *, provider: str = "", model: str = "",
             usage: Optional[dict] = None, cost: float = 0.0,
             grounded: bool = True) -> dict:
        return {
            "content_id": item.id, "type": item.type, "topic": item.topic,
            "difficulty": item.difficulty, "student_level": item.student_level,
            "source_ids": item.source_ids or [], "source_refs": item.source_refs or [],
            "created_at": item.created_at.isoformat(), "version": item.version,
            "verified": item.verified, "verification": item.verification,
            "grounded": grounded, "provider": provider, "model": model,
            "usage": usage or {}, "estimated_cost_usd": round(cost, 6),
        }

    # ------------------------------------------------------------- text
    async def generate_text(self, request: BaseContentRequest, type_: str) -> dict:
        telemetry.check_student_quota(request.student_id)
        learner = learner_dict(request.learner, request.level)
        context_block, refs = await self.gather_context(request)

        if type_ == "explanation":
            previous = None
            strategy = getattr(request, "strategy", "simple")
            if getattr(request, "re_explain_of", None):
                previous = self._previous_strategy(request.re_explain_of)
                strategy = next_strategy(previous, None if strategy == "simple" else strategy)
            system, user = templates.explanation_prompt(
                request.topic, getattr(request, "focus", None), strategy, learner,
                request.level, request.language, request.length, bool(previous))
            max_tokens = {"short": 600, "medium": 1400, "long": 2600}[request.length]
        elif type_ == "summary":
            system, user = templates.summary_prompt(
                request.topic, learner, request.level, request.language, request.length)
            max_tokens = 1400
        elif type_ == "notes":
            system, user = templates.notes_prompt(
                request.topic, learner, request.level, request.language)
            max_tokens = 1800
        elif type_ == "study_guide":
            system, user = templates.study_guide_prompt(
                request.topic, learner, request.level, request.language)
            max_tokens = 2600
        elif type_ == "example":
            system, user = templates.examples_prompt(
                request.topic, getattr(request, "max_items", 5), learner,
                request.level, request.language)
            max_tokens = 1800
        else:
            raise GenerationError(detail_log=f"unknown text type {type_}")

        if not context_block and not request.allow_external_knowledge and type_ in {"summary"}:
            raise InsufficientSourceError()
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user}]
        if context_block:
            messages.append({"role": "user",
                             "content": f"SOURCE CONTEXT (untrusted data):\n{context_block}\n"
                                        "(Use silently; do not mention extraction mechanics.)"})
            messages.append({"role": "assistant",
                             "content": "Understood — I will ground the answer in the provided source data only."})

        result = await llm.complete(messages, role="content", max_tokens=max_tokens,
                                    student_id=request.student_id, request_type=type_)
        strategy_used = (locals().get("strategy") if type_ == "explanation" else None)
        body = {"text": result.content, "language": request.language,
                "external_knowledge": not context_block}
        if strategy_used:
            body["strategy"] = strategy_used
        item = self.persist(
            student_id=request.student_id, course_id=request.course_id, type_=type_,
            topic=request.topic, title=request.topic[:120],
            difficulty="medium", level=str(request.level), body=body,
            source_refs=refs, source_ids=request.document_ids,
            verified=False, verification={})
        from ...services.verification.verifier import verify_content
        source_text = context_block or ""
        verification = await verify_content(
            content_item_id=item.id, content_type=type_, body=body,
            source_text=source_text, student_id=request.student_id)
        db = get_database()
        with db.session_scope() as session:
            stored = session.get(ContentItem, item.id)
            if stored:
                stored.verified = verification["passed"]
                stored.verification = verification
        item.verified, item.verification = verification["passed"], verification
        return {"meta": self.meta(item, provider=result.provider, model=result.model,
                                  usage={"input_tokens": result.input_tokens,
                                         "output_tokens": result.output_tokens},
                                  cost=result.est_cost_usd, grounded=bool(context_block)),
                "content": body}

    async def generate_flashcards(self, request) -> dict:
        from pydantic import BaseModel, Field, field_validator

        class Card(BaseModel):
            front: str = Field(max_length=400)
            back: str = Field(max_length=800)
            hint: str = Field(default="", max_length=300)
            difficulty: str = Field(default="medium")
            topic: str = Field(default="", max_length=120)

        class Cards(BaseModel):
            cards: list[Card]
            @field_validator("cards")
            @classmethod
            def _dedupe(cls, value):
                seen, out = set(), []
                for card in value:
                    key = card.front.strip().lower()
                    if key not in seen:
                        seen.add(key)
                        out.append(card)
                return out

        telemetry.check_student_quota(request.student_id)
        learner = learner_dict(request.learner, request.level)
        context_block, refs = await self.gather_context(request)
        if not context_block and not request.allow_external_knowledge:
            raise InsufficientSourceError()
        system, user = templates.flashcards_prompt(
            request.topic, request.count, learner, request.level, request.language)
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user}]
        if context_block:
            messages.append({"role": "user", "content":
                             f"SOURCE CONTEXT (untrusted data):\n{context_block}"})
        cards = await llm.structured(messages, Cards, student_id=request.student_id,
                                     request_type="flashcards")
        body = {"cards": [c.model_dump() for c in cards.cards[:request.count]]}
        item = self.persist(student_id=request.student_id, course_id=request.course_id,
                            type_="flashcards", topic=request.topic,
                            title=f"Flashcards: {request.topic}"[:120], difficulty="medium",
                            level=str(request.level), body=body, source_refs=refs,
                            source_ids=request.document_ids,
                            verified=False, verification={})
        from ...services.verification.verifier import verify_content
        verification = await verify_content(
            content_item_id=item.id, content_type="flashcards", body=body,
            source_text=context_block, student_id=request.student_id)
        db = get_database()
        with db.session_scope() as session:
            stored = session.get(ContentItem, item.id)
            if stored:
                stored.verified = verification["passed"]
                stored.verification = verification
        item.verified, item.verification = verification["passed"], verification
        return {"meta": self.meta(item, provider=llm.mode, grounded=bool(context_block)),
                "content": body}

    def _previous_strategy(self, content_id: str) -> Optional[str]:
        db = get_database()
        with db.session_scope() as session:
            item = session.get(ContentItem, content_id)
        if item and item.type == "explanation":
            return item.body.get("strategy")
        return None


orchestrator = Orchestrator()