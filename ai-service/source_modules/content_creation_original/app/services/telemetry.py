"""Telemetry — provider usage/cost persistence (spec #35, #36) + Langfuse hook.

Also enforces per-student daily cost quotas (cost abuse prevention)."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Optional

from ..core.logging import get_logger
from ..core.security import new_id
from ..db import get_database
from ..db.models import ProviderRequest

log = get_logger("telemetry")

DAILY_COST_LIMIT_USD = 5.0
DAILY_REQUEST_LIMIT = 600


class Telemetry:
    def record_llm(self, *, student_id: Optional[str], result, request_type: str,
                   status: str) -> None:
        """Persist usage + forward to observability. Never blocks the caller."""
        def _write() -> None:
            try:
                db = get_database()
                with db.session_scope() as session:
                    session.add(ProviderRequest(
                        id=new_id(), student_id=student_id, provider=result.provider,
                        model=result.model, request_type=request_type,
                        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
                        est_cost_usd=result.est_cost_usd, latency_ms=result.latency_ms,
                        status=status))
            except Exception as exc:  # noqa: BLE001
                log.warning("telemetry_write_failed", extra={"ctx": {"err": str(exc)[:120]}})

        def _observe() -> None:
            try:
                from ..providers.observability.langfuse import observability
                observability.track_generation(
                    request_id="-", student_id=student_id, provider=result.provider,
                    model=result.model, request_type=request_type,
                    input_tokens=result.input_tokens, output_tokens=result.output_tokens,
                    est_cost_usd=result.est_cost_usd, latency_ms=result.latency_ms,
                    status=status)
            except Exception:  # noqa: BLE001
                pass

        asyncio.get_running_loop().run_in_executor(None, _write)
        asyncio.get_running_loop().run_in_executor(None, _observe)

    def record_provider(self, *, student_id: Optional[str], provider: str, model: str,
                        request_type: str, est_cost_usd: float = 0.0,
                        latency_ms: int = 0, status: str = "ok") -> None:
        try:
            db = get_database()
            with db.session_scope() as session:
                session.add(ProviderRequest(
                    id=new_id(), student_id=student_id, provider=provider, model=model,
                    request_type=request_type, est_cost_usd=est_cost_usd,
                    latency_ms=latency_ms, status=status))
        except Exception as exc:  # noqa: BLE001
            log.warning("telemetry_write_failed", extra={"ctx": {"err": str(exc)[:120]}})

    def student_usage_today(self, student_id: str) -> dict:
        from sqlalchemy import func, select
        db = get_database()
        with db.session_scope() as session:
            since = _utcnow() - timedelta(hours=24)
            count, cost = session.execute(
                select(func.count(ProviderRequest.id),
                       func.coalesce(func.sum(ProviderRequest.est_cost_usd), 0.0))
                .where(ProviderRequest.student_id == student_id,
                       ProviderRequest.created_at >= since)).one()
            return {"requests_24h": int(count), "cost_usd_24h": round(float(cost), 4),
                    "limits": {"requests": DAILY_REQUEST_LIMIT, "cost_usd": DAILY_COST_LIMIT_USD}}

    def check_student_quota(self, student_id: str) -> None:
        from ..core.exceptions import QuotaExceededError
        usage = self.student_usage_today(student_id)
        if (usage["requests_24h"] >= DAILY_REQUEST_LIMIT
                or usage["cost_usd_24h"] >= DAILY_COST_LIMIT_USD):
            raise QuotaExceededError()


def _utcnow():
    from ..db.models import utcnow
    return utcnow()


telemetry = Telemetry()