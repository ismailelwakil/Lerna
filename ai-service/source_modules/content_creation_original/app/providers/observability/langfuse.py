"""Langfuse observability (spec #36) — real ingestion API, fire-and-forget,
fails silently when unconfigured. Never logs secrets or full documents."""
from __future__ import annotations

import base64
import threading
import time
from typing import Optional

import httpx

from ...core.config import get_settings
from ...core.logging import get_logger

log = get_logger("langfuse")


class NullObservability:
    name = "null"

    def track_generation(self, **kwargs) -> None:
        pass

    def health(self) -> dict:
        return {"provider": "observability", "name": "null", "configured": False}


class LangfuseObservability:
    name = "langfuse"

    def __init__(self) -> None:
        s = get_settings()
        self._url = f"{s.langfuse_base_url}/api/public/ingestion"
        token = base64.b64encode(
            f"{s.langfuse_public_key}:{s.langfuse_secret_key}".encode()).decode()
        self._headers = {"Authorization": f"Basic {token}",
                         "Content-Type": "application/json"}

    def track_generation(self, *, request_id: str, student_id: Optional[str],
                         provider: str, model: str, request_type: str,
                         input_tokens: int, output_tokens: int, est_cost_usd: float,
                         latency_ms: int, status: str, metadata: Optional[dict] = None) -> None:
        event = {
            "id": f"gen-{request_id}-{int(time.time()*1000)}",
            "type": "generation-event",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "body": {
                "id": f"gen-{request_id}",
                "name": request_type,
                "model": model,
                "modelParameters": {},
                "usage": {"promptTokens": input_tokens, "completionTokens": output_tokens},
                "cost": est_cost_usd,
                "metadata": {"provider": provider, "status": status,
                             "latency_ms": latency_ms, **(metadata or {})},
            },
        }

        def _send() -> None:
            try:
                httpx.post(self._url, headers=self._headers,
                           json={"batch": [event], "metadata": {
                               "student_ref": bool(student_id)}}, timeout=10.0)
            except httpx.HTTPError:
                pass  # observability must never break generation

        threading.Thread(target=_send, daemon=True).start()

    def health(self) -> dict:
        return {"provider": "observability", "name": "langfuse", "configured": True}


def _build():
    s = get_settings()
    if s.langfuse_public_key and s.langfuse_secret_key:
        try:
            return LangfuseObservability()
        except Exception:  # noqa: BLE001
            return NullObservability()
    return NullObservability()


observability = _build()