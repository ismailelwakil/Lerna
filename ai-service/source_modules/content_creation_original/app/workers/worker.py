"""Async job system (spec #37) — DB-persisted jobs + in-process asyncio
workers (production-viable single-node; Redis-ready: swap JobExecutor for
Celery/RQ — the worker functions are plain callables)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta

from ..core.logging import get_logger
from ..core.security import new_id
from ..db import get_database
from ..db.models import GenerationJob

log = get_logger("jobs")

VALID_KINDS = {"document_process", "audio", "video", "exam", "embeddings"}


def utcnow() -> datetime:
    """Timezone-aware UTC, stored naive for DB compatibility (matches
    app/db/models.utcnow — deprecated datetime.utcnow removed)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JobExecutor:
    def __init__(self, concurrency: int = 4) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._concurrency = concurrency
        self._handlers: dict[str, object] = {}

    def register(self, kind: str, handler) -> None:
        self._handlers[kind] = handler

    async def start(self) -> None:
        for i in range(self._concurrency):
            self._workers.append(asyncio.create_task(self._run(i)))
        log.info("job_workers_started", extra={"ctx": {"workers": self._concurrency}})

    async def stop(self) -> None:
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

    async def submit(self, job_id: str, kind: str) -> None:
        await self._queue.put((job_id, kind))

    async def _run(self, worker_id: int) -> None:
        while True:
            job_id, kind = await self._queue.get()
            try:
                handler = self._handlers.get(kind)
                if handler is None:
                    await self.fail(job_id, f"no handler for kind '{kind}'")
                    continue
                db = get_database()
                with db.session_scope() as session:
                    job = session.get(GenerationJob, job_id)
                    if job is None:
                        continue
                    job.status = "PROCESSING" if kind != "video" else "PLANNING"
                    params = job.params
                await handler(job_id, params)
            except Exception as exc:  # noqa: BLE001 — jobs must never crash workers
                await self.fail(job_id, str(exc)[:400])
                log.error("job_failed", extra={"ctx": {"job": job_id, "err": str(exc)[:200]}})
            finally:
                self._queue.task_done()

    @staticmethod
    async def fail(job_id: str, message: str) -> None:
        db = get_database()
        with db.session_scope() as session:
            job = session.get(GenerationJob, job_id)
            if job:
                job.status = "FAILED"
                job.error = message
                job.updated_at = utcnow()


def create_job(*, student_id: str, kind: str, params: dict) -> GenerationJob:
    db = get_database()
    with db.session_scope() as session:
        job = GenerationJob(id=new_id(), student_id=student_id, kind=kind,
                            status="QUEUED", params=params)
        session.add(job)
        return job


def job_out(job: GenerationJob) -> dict:
    return {"job_id": job.id, "kind": job.kind, "status": job.status,
            "progress": job.progress, "result": job.result, "error": job.error,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()}


executor = JobExecutor()


# ------------------------------------------------------------- handlers
async def handle_document_process(job_id: str, params: dict) -> None:
    from ..services.documents.pipeline import process_document_job
    await process_document_job(job_id, params)


async def handle_audio(job_id: str, params: dict) -> None:
    from ..services.media_service import store_asset
    from ..providers.tts.voice import tts
    db = get_database()
    with db.session_scope() as session:
        job = session.get(GenerationJob, job_id)
        text, voice, student_id = (job.params.get("text", ""),
                                   job.params.get("voice"), job.student_id)
        job.status, job.progress = "PROCESSING", 20
    result = await tts.synthesize(text, voice=voice, speed=1.0)
    asset = await store_asset(student_id=student_id, kind="audio",
                              data=result.audio_bytes, mime=result.mime,
                              ext=".mp3", job_id=job_id,
                              asset_meta={"chars": len(text)})
    with db.session_scope() as session:
        job = session.get(GenerationJob, job_id)
        job.status, job.progress, job.result = "COMPLETED", 100, {"asset": asset}


async def handle_video(job_id: str, params: dict) -> None:
    from ..services.media_service import video_service
    db = get_database()

    def progress(pct: int, stage: str) -> None:
        with db.session_scope() as session:
            job = session.get(GenerationJob, job_id)
            if job:
                job.progress, job.status = pct, stage

    with db.session_scope() as session:
        job = session.get(GenerationJob, job_id)
        if job is None:
            return
        job_obj = job
        student_id, params_data = job.student_id, dict(job.params)
    result = await video_service.generate(
        job_obj, student_id=student_id, topic=params_data.get("topic", ""),
        level=params_data.get("level", "beginner"),
        language=params_data.get("language", "en"),
        duration=params_data.get("duration_seconds", 180),
        voice=params_data.get("voice"), source_context=params_data.get("source_context", ""),
        progress=progress)
    with db.session_scope() as session:
        job = session.get(GenerationJob, job_id)
        job.status, job.progress, job.result = "COMPLETED", 100, result


async def handle_exam(job_id: str, params: dict) -> None:
    from ..services.assessment.exam_generator import exam_generator
    db = get_database()
    with db.session_scope() as session:
        job = session.get(GenerationJob, job_id)
        job.status, job.progress = "PROCESSING", 30
    result = await exam_generator.generate(
        student_id=job.student_id, kind=params.get("kind", "exam"),
        topic=params.get("topic", ""), num_questions=params.get("num_questions", 10),
        difficulty=params.get("difficulty", "medium"), mix=True,
        question_types=params.get("question_types", ["MCQ", "TRUE_FALSE", "SHORT_ANSWER"]),
        level=params.get("level", "beginner"), language=params.get("language", "en"),
        objectives=params.get("objectives", []), course_id=params.get("course_id"),
        document_id=params.get("document_id"),
        source_texts=params.get("source_texts", []), source_chunks=[])
    with db.session_scope() as session:
        job = session.get(GenerationJob, job_id)
        job.status, job.progress, job.result = "COMPLETED", 100, {
            "set_id": result["set_id"], "total": result["total"]}


def register_handlers() -> None:
    executor.register("document_process", handle_document_process)
    executor.register("audio", handle_audio)
    executor.register("video", handle_video)
    executor.register("exam", handle_exam)
    executor.register("embeddings", handle_document_process)  # re-index path


def count_recent_jobs(student_id: str, kind: str, hours: int = 24) -> int:
    from sqlalchemy import func, select
    db = get_database()
    with db.session_scope() as session:
        return int(session.scalar(
            select(func.count(GenerationJob.id)).where(
                GenerationJob.student_id == student_id,
                GenerationJob.kind == kind,
                GenerationJob.created_at >= utcnow() - timedelta(hours=hours))) or 0)