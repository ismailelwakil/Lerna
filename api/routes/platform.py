"""
Platform AI task execution (used by the GenAI platform backend).
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import get_ai_service
from src.integration.service import LearningIntelligenceModule
from src.platform.tasks import TaskError, run_task

router = APIRouter(prefix="/platform", tags=["Platform AI tasks"])


class PlatformTaskRequest(BaseModel):
    task: str = Field(..., min_length=2, max_length=80)
    system: Optional[str] = Field(default=None, max_length=40000)
    input: Any
    language: Optional[str] = None


class PlatformTaskResponse(BaseModel):
    task: str
    output: dict
    provider: str
    model: str


@router.post("/tasks/run", response_model=PlatformTaskResponse)
def run_platform_task(
    body: PlatformTaskRequest,
    ai: LearningIntelligenceModule = Depends(get_ai_service),
):
    """Run one structured AI task and return its JSON output."""
    try:
        return run_task(ai, body.task, body.system, body.input, body.language)
    except TaskError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc))
