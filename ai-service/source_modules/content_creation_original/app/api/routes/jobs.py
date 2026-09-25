"""Job + asset routes (spec #37, #40)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core.exceptions import NotFoundError
from ...db import get_database
from ...db.models import GenerationJob
from ...schemas.documents import JobCreateRequest
from ..dependencies import authorize_student, rate, student_identity
# NOTE: aliased import — a previous direct import of `create_job` collided
# with the endpoint function of the same name, making the endpoint call
# itself (500). Covered by regression tests.
from ...workers.worker import VALID_KINDS, executor, job_out
from ...workers.worker import create_job as create_generation_job

router = APIRouter(prefix="/jobs")


@router.post("")
async def create_job(payload: JobCreateRequest,
                     student: str = Depends(student_identity),
                     _rl: None = Depends(rate("jobs"))):
    """Enqueue a generation job under the AUTHENTICATED identity."""
    if payload.kind not in VALID_KINDS:
        from ...core.exceptions import ValidationError
        raise ValidationError(f"kind must be one of {sorted(VALID_KINDS)}")
    authorize_student(student, payload.student_id)  # body id cannot override
    job = create_generation_job(student_id=student, kind=payload.kind,
                                params=payload.params)
    await executor.submit(job.id, payload.kind)
    return job_out(job)


@router.get("/{job_id}", dependencies=[Depends(rate("default"))])
async def get_job(job_id: str, student: str = Depends(student_identity)):
    return _owned(job_id, student)


@router.get("/{job_id}/status", dependencies=[Depends(rate("default"))])
async def job_status(job_id: str, student: str = Depends(student_identity)):
    job = _owned(job_id, student)
    return {"job_id": job_id, "status": job["status"], "progress": job["progress"],
            "error": job["error"]}


def _owned(job_id: str, student_id: str) -> dict:
    """Ownership-aware lookup: id AND owner in one query (no existence oracle)."""
    from sqlalchemy import select
    db = get_database()
    with db.session_scope() as session:
        job = session.scalar(
            select(GenerationJob).where(GenerationJob.id == job_id,
                                        GenerationJob.student_id == student_id))
        if job is None:
            raise NotFoundError("Job not found.")  # uniform 404: no existence oracle
        return job_out(job)