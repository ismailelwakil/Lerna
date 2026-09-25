"""Content routes — text, flashcards, from-document, diagram, image, audio,
video, verify. Thin handlers: validate → orchestrator → typed response."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...core.config import get_settings
from ...core.exceptions import ProviderUnavailableError
from ...core.logging import get_logger
from ...db import get_database
from ...db.models import ContentItem
from ...schemas.common import BaseContentRequest
from ...schemas.documents import (AudioRequest, DiagramRequest, ExplainRequest,
                                  FlashcardsRequest, FromDocumentRequest,
                                  ImageRequest, TextRequest, VerifyRequest,
                                  VideoRequest)
from ...services.orchestrator.intent_router import intent_router
from ...services.orchestrator.orchestrator import orchestrator
from ...services.telemetry import telemetry
from ..dependencies import audit, authorize_student, quota_guard, rate, student_identity

log = get_logger("api.content")
router = APIRouter()


@router.post("/explain")
async def explain(request: ExplainRequest,
                  student: str = Depends(student_identity),
                  _rl: None = Depends(rate("generate"))):
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(request.student_id)
    audit("explain", student_id=request.student_id, topic=request.topic[:60])
    return await orchestrator.generate_text(request, "explanation")


@router.post("/summarize")
async def summarize(request: TextRequest,
                    student: str = Depends(student_identity),
                    _rl: None = Depends(rate("generate"))):
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(request.student_id)
    return await orchestrator.generate_text(request, "summary")


@router.post("/notes")
async def notes(request: TextRequest,
                student: str = Depends(student_identity),
                _rl: None = Depends(rate("generate"))):
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(request.student_id)
    return await orchestrator.generate_text(request, "notes")


@router.post("/study-guide")
async def study_guide(request: TextRequest,
                      student: str = Depends(student_identity),
                      _rl: None = Depends(rate("generate"))):
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(request.student_id)
    return await orchestrator.generate_text(request, "study_guide")


@router.post("/examples")
async def examples(request: TextRequest,
                   student: str = Depends(student_identity),
                   _rl: None = Depends(rate("generate"))):
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(request.student_id)
    return await orchestrator.generate_text(request, "example")


@router.post("/flashcards")
async def flashcards(request: FlashcardsRequest,
                     student: str = Depends(student_identity),
                     _rl: None = Depends(rate("generate"))):
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(request.student_id)
    return await orchestrator.generate_flashcards(request)


@router.post("/from-document")
async def from_document(request: FromDocumentRequest,
                        student: str = Depends(student_identity),
                        _rl: None = Depends(rate("generate"))):
    """Natural language: 'Summarize this.' / 'Create 20 MCQs.' / 'Teach me.'"""
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(request.student_id)
    for document_id in request.document_ids:
        orchestrator.owned_document(request.student_id, document_id)  # IDOR guard
    intent = await intent_router.classify(request.instruction, request.student_id)
    base = intent_router.to_content_request(request, intent)
    mapping = {"summarize": "summary", "explain": "explanation", "teach": "explanation",
               "notes": "notes", "study_guide": "study_guide",
               "difficult_concepts": "summary"}
    if intent.intent in mapping:
        if intent.intent in {"teach", "explain"}:
            base.topic = request.instruction[:200]
        return await orchestrator.generate_text(base, mapping[intent.intent])
    if intent.intent == "flashcards":
        from ...schemas.documents import FlashcardsRequest as FR
        fr = FR(student_id=request.student_id, topic="uploaded material",
                document_ids=request.document_ids, level=base.level,
                language=base.language, count=intent.count or 12,
                allow_external_knowledge=request.allow_external_knowledge)
        return await orchestrator.generate_flashcards(fr)
    if intent.intent in {"quiz", "exam"}:
        from ...services.assessment.exam_generator import exam_generator
        from ...services.rag.rag_service import rag
        chunks = await rag.retrieve(request.student_id, request.instruction,
                                    document_ids=request.document_ids, k=6)
        return await exam_generator.generate(
            student_id=request.student_id, kind="quiz" if intent.intent == "quiz" else "exam",
            topic=request.instruction[:200],
            num_questions=intent.count or 10, difficulty="medium", mix=True,
            question_types=["MCQ", "TRUE_FALSE", "SHORT_ANSWER"],
            level=str(base.level), language=base.language, objectives=[],
            course_id=None, document_id=request.document_ids[0],
            source_texts=[c.text for c in chunks], source_chunks=chunks)
    if intent.intent == "audio":
        chunks = await (await _rag()).retrieve(
            request.student_id, request.instruction, document_ids=request.document_ids)
        text = "\n\n".join(c.text for c in chunks)[: get_settings().max_audio_chars]
        from ...services.media_service import audio_service
        return await audio_service.synthesize(student_id=request.student_id, text=text,
                                              voice=None, speed=1.0)
    raise ProviderUnavailableError(
        f"Intent '{intent.intent}' is not available from this endpoint yet.",
        code="INTENT_UNSUPPORTED")


async def _rag():
    from ...services.rag.rag_service import rag
    return rag


@router.post("/diagram")
async def diagram(request: DiagramRequest,
                  student: str = Depends(student_identity),
                  _rl: None = Depends(rate("generate"))):
    """Deterministic (SVG) diagrams — exact labels, no generative pixels."""
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(request.student_id)
    from ...services.images.diagram import diagram_service
    from ...services.personalization.service import learner_dict
    context_block, refs = await orchestrator.gather_context(
        _as_base(request))
    svg, spec = await diagram_service.create(
        topic=request.topic, kind=request.diagram_kind,
        learner=learner_dict(request.learner, request.level), level=str(request.level),
        language=request.language, source_context=context_block,
        style_hint=request.style_hint)
    from ...services.media_service import store_asset
    asset = await store_asset(student_id=request.student_id, kind="image",
                              data=svg.encode(), mime="image/svg+xml", ext=".svg",
                              asset_meta={"diagram_kind": spec.kind})
    item = orchestrator.persist(
        student_id=request.student_id, course_id=request.course_id, type_="diagram",
        topic=request.topic, title=spec.title, difficulty="medium",
        level=str(request.level), body={"svg": svg[:100000], "spec": spec.model_dump()},
        source_refs=refs, source_ids=request.document_ids, verified=True,
        verification={"passed": True, "checker": "deterministic-renderer"})
    return {"meta": orchestrator.meta(item, provider="deterministic", model="svg"),
            **asset, "svg_inline": svg}


def _as_base(request) -> BaseContentRequest:
    return BaseContentRequest(
        student_id=request.student_id, course_id=request.course_id, topic=request.topic,
        inline_material=request.inline_material, document_ids=request.document_ids,
        level=request.level, language=request.language, length=request.length,
        allow_external_knowledge=request.allow_external_knowledge, learner=request.learner)


@router.post("/image")
async def image(request: ImageRequest,
                student: str = Depends(student_identity),
                _rl: None = Depends(rate("expensive"))):
    """Generative illustrations (Gemini) — for concepts where exactness of
    labels is NOT critical (use /diagram for exact technical diagrams)."""
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(request.student_id)
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ProviderUnavailableError("Gemini image generation is not configured.",
                                       code="IMAGE_PROVIDER_UNAVAILABLE")
    from ...providers.image.gemini_media import GeminiImageProvider
    context_block, _refs = await orchestrator.gather_context(_as_base(request))
    style = {"illustration": "a clean educational illustration of",
             "infographic": "an educational infographic about",
             "thumbnail": "a bold educational video thumbnail about"}[request.visual_kind]
    prompt = (f"{style} '{request.topic}' for a {request.level} learner. "
              f"No embedded long text passages; label key parts clearly "
              f"only where natural. Aspect ratio {request.aspect}.")
    result = await GeminiImageProvider().generate(prompt, aspect=request.aspect)
    from ...services.media_service import store_asset
    asset = await store_asset(student_id=request.student_id, kind="image",
                              data=result.image_bytes, mime=result.mime,
                              ext=".png", asset_meta={"model": result.model})
    telemetry.record_provider(student_id=request.student_id, provider="gemini",
                              model=result.model, request_type="image")
    item = orchestrator.persist(
        student_id=request.student_id, course_id=request.course_id, type_="image",
        topic=request.topic, title=f"Illustration: {request.topic}"[:120],
        difficulty="medium", level=str(request.level),
        body={"asset_id": asset["asset_id"]}, source_refs=[], source_ids=[],
        verified=False, verification={"checker": "none",
                                      "note": "generative image — review by tutor"})
    return {"meta": orchestrator.meta(item, provider="gemini", model=result.model),
            **asset}


@router.post("/audio")
async def audio(request: AudioRequest,
                student: str = Depends(student_identity),
                _rl: None = Depends(rate("expensive"))):
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(request.student_id)
    text = request.text_override
    if not text:
        chunks = await (await _rag()).retrieve(
            request.student_id, request.topic, document_ids=request.document_ids, k=8)
        text = "\n\n".join(c.text for c in chunks)
        if not text:
            from ...core.exceptions import InsufficientSourceError
            raise InsufficientSourceError()
    if request.async_mode or len(text) > get_settings().max_audio_chars:
        from ...workers.worker import create_job, executor
        job = create_job(student_id=student, kind="audio",
                         params={"text": text[:50000], "voice": request.voice})
        await executor.submit(job.id, "audio")
        return {"job": {"job_id": job.id, "status": "QUEUED"},
                "note": "large audio generation runs as a job — poll /jobs/{id}"}
    from ...services.media_service import audio_service
    asset = await audio_service.synthesize(student_id=request.student_id, text=text,
                                           voice=request.voice, speed=request.speed)
    return asset


@router.post("/video")
async def video(request: VideoRequest,
                student: str = Depends(student_identity),
                _rl: None = Depends(rate("expensive"))):
    """Async pipeline (spec #21) — returns a job immediately."""
    request.student_id = authorize_student(student, request.student_id)
    quota_guard(student)
    from ...workers.worker import count_recent_jobs, create_job, executor
    settings = get_settings()
    if count_recent_jobs(request.student_id, "video") >= settings.max_video_jobs_per_day:
        from ...core.exceptions import QuotaExceededError
        raise QuotaExceededError("Daily video generation limit reached.")
    context_block, refs = await orchestrator.gather_context(_as_base(request))
    job = create_job(student_id=student, kind="video", params={
        "topic": request.topic, "level": str(request.level),
        "language": request.language, "duration_seconds": request.duration_seconds,
        "voice": request.voice, "source_context": context_block[:12000],
        "document_ids": request.document_ids})
    await executor.submit(job.id, "video")
    audit("video_job", student_id=request.student_id, topic=request.topic[:60])
    return {"job_id": job.id, "status": "QUEUED",
            "states": ["QUEUED", "PLANNING", "SCRIPTING", "VERIFYING",
                       "SCENE_GENERATION", "ASSEMBLING", "QUALITY_CHECK", "COMPLETED"]}


@router.post("/verify")
async def verify(request: VerifyRequest,
                 student: str = Depends(student_identity),
                 _rl: None = Depends(rate("default"))):
    """Re-verify content owned by the AUTHENTICATED student (object-level
    authorization: row looked up by id AND owner in a single query)."""
    from sqlalchemy import select
    db = get_database()
    with db.session_scope() as session:
        item = session.scalar(
            select(ContentItem).where(ContentItem.id == request.content_id,
                                      ContentItem.student_id == student))
        if item is None:
            from ...core.exceptions import NotFoundError
            raise NotFoundError("Content item not found.")  # uniform 404: no existence oracle
        body, type_, student_id = item.body, item.type, item.student_id
    quota_guard(student_id)
    from ...services.verification.verifier import verify_content
    result = await verify_content(
        content_item_id=request.content_id, content_type=type_, body=body,
        source_text="", student_id=student_id)
    return {"content_id": request.content_id, **result}


@router.get("/assets/{key_path:path}")
async def asset(key_path: str, exp: str = Query(...), sig: str = Query(...)):
    """Private asset access — only via short-lived HMAC-signed URLs (spec #40)."""
    from ...core.security import verify_signed
    from ...providers.storage.storage import storage
    if not verify_signed(key_path, exp, sig):
        from ...core.exceptions import ForbiddenError
        raise ForbiddenError("Invalid or expired asset link.")
    data = await storage.get(key_path)
    from ...core.security import ALLOWED_EXTENSIONS
    import pathlib
    ext = pathlib.Path(key_path).suffix.lower()
    from fastapi.responses import Response
    return Response(content=data,
                    media_type=ALLOWED_EXTENSIONS.get(ext, "application/octet-stream"))