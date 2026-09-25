"""OpenRouter LLM provider — primary text/reasoning engine.

* configurable model registry validated against the LIVE catalog (#4, #50)
* retries, timeouts, per-role fallback chain: role model → fast model →
  Groq → OpenAI (whichever are configured) (#34)
* structured JSON generation validated by Pydantic with one repair retry (#4)
* token/cost tracking surfaced to telemetry (#35)
* offline MockLLM for tests (no keys needed) (#44)
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ...core.config import get_settings
from ...core.exceptions import GenerationError, SchemaValidationError
from ...core.logging import get_logger
from ..base import LLMResult

log = get_logger("llm")
T = TypeVar("T", bound=BaseModel)

RETRYABLE = {408, 409, 429, 500, 502, 503, 504}


class MockLLM:
    """Deterministic offline provider for CI/tests (CONTENT_LLM_MODE=mock)."""
    name = "mock"

    async def complete(self, messages, *, model: str, max_tokens: int,
                       temperature: float, student_id=None, request_type="") -> "LLMResult":
        await asyncio.sleep(0.02)
        return LLMResult(content="(mock answer)", model=model, provider="mock",
                         input_tokens=50, output_tokens=20, latency_ms=5)

    async def structured(self, messages, schema: Type[T], *, student_id=None,
                         request_type="") -> T:
        raise GenerationError("mock provider cannot produce structured data",
                              detail_log="mock structured")


class OpenRouterProvider:
    name = "openrouter"

    def __init__(self) -> None:
        s = get_settings()
        self._settings = s
        self._client = httpx.AsyncClient(
            base_url=s.openrouter_base,
            headers={"Authorization": f"Bearer {s.openrouter_api_key}",
                     "Content-Type": "application/json",
                     "HTTP-Referer": "https://edunation.app", "X-Title": "EDUnation Content"},
            timeout=httpx.Timeout(s.llm_timeout, connect=15.0))
        self._catalog: Optional[dict[str, dict]] = None  # id -> {pricing, context}
        self._catalog_ts = 0.0

    async def aclose(self) -> None:
        await self._client.aclose()

    # ----------------------------------------------------------- catalog
    async def catalog(self, ttl_seconds: float = 3600) -> dict[str, dict]:
        now = time.time()
        if self._catalog and now - self._catalog_ts < ttl_seconds:
            return self._catalog
        try:
            resp = await self._client.get("/models")
            if resp.status_code == 200:
                self._catalog = {m["id"]: m for m in resp.json().get("data", [])}
                self._catalog_ts = now
        except httpx.HTTPError as exc:
            log.warning("catalog_fetch_failed", extra={"ctx": {"err": str(exc)[:160]}})
            if self._catalog is None:
                self._catalog = {}
        return self._catalog or {}

    async def resolve_model(self, role: str) -> str:
        """Configured model for the role; falls back to a live-catalog model
        when the configured id doesn't exist (never fabricate ids)."""
        settings = get_settings()
        wanted = settings.models.get(role) or settings.models["fast"]
        catalog = await self.catalog()
        if not catalog or wanted in catalog:
            return wanted
        alternatives = {
            "fast": "google/gemini-2.5-flash", "reasoning": "openai/gpt-5",
            "content": "anthropic/claude-sonnet-4.5", "structured": "google/gemini-2.5-flash"}
        fallback = next((m for m in (alternatives.get(role), *settings.models.values())
                         if m in catalog), next(iter(catalog)))
        log.warning("configured_model_not_in_catalog",
                    extra={"ctx": {"role": role, "wanted": wanted, "using": fallback}})
        return fallback

    def _price_per_mtok(self, model_id: str) -> tuple[float, float]:
        entry = (self._catalog or {}).get(model_id) or {}
        pricing = entry.get("pricing") or {}
        try:
            p = float(pricing.get("prompt", 0)) * 1_000_000
            c = float(pricing.get("completion", 0)) * 1_000_000
            return p, c
        except (TypeError, ValueError):
            return 0.5, 1.5

    # ------------------------------------------------------------ chat
    async def complete(self, messages: list[dict], *, model: str,
                       max_tokens: int = 2000, temperature: float = 0.4,
                       student_id: Optional[str] = None,
                       request_type: str = "text") -> "LLMResult":
        from ...services.telemetry import telemetry  # local import (no cycle)
        started = time.perf_counter()
        attempts = 3
        last_exc: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                resp = await self._client.post("/chat/completions", json={
                    "model": model, "messages": messages,
                    "max_tokens": max_tokens, "temperature": temperature})
                if resp.status_code in RETRYABLE and attempt < attempts - 1:
                    await asyncio.sleep(0.7 * (2 ** attempt))
                    continue
                if resp.status_code >= 400:
                    raise GenerationError(detail_log=f"openrouter {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
                choice = data["choices"][0]
                usage = data.get("usage") or {}
                in_tok = int(usage.get("prompt_tokens") or 0)
                out_tok = int(usage.get("completion_tokens") or 0)
                p, c = self._price_per_mtok(model)
                cost = in_tok / 1e6 * p + out_tok / 1e6 * c
                result = LLMResult(
                    content=choice["message"].get("content") or "",
                    model=data.get("model") or model, provider=self.name,
                    input_tokens=in_tok, output_tokens=out_tok, est_cost_usd=round(cost, 6),
                    latency_ms=int((time.perf_counter() - started) * 1000))
                telemetry.record_llm(student_id=student_id, result=result,
                                     request_type=request_type, status="ok")
                return result
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                if attempt < attempts - 1:
                    await asyncio.sleep(0.7 * (2 ** attempt))
        raise GenerationError(detail_log=f"openrouter transport failure: {last_exc}")

    async def structured(self, messages: list[dict], schema: Type[T], *,
                         student_id: Optional[str] = None,
                         request_type: str = "structured",
                         max_tokens: int = 4000) -> T:
        """JSON generation validated against a Pydantic schema; one repair retry."""
        model = await self.resolve_model("structured")
        repair = ""
        for attempt in range(2):
            payload_messages = messages + ([{"role": "user", "content": repair}] if repair else [])
            result = await self.complete(
                payload_messages, model=model, max_tokens=max_tokens,
                temperature=0.2 if attempt else 0.4,
                student_id=student_id, request_type=request_type)
            parsed = _extract_json(result.content)
            if parsed is None:
                repair = ("Your previous reply was not valid JSON. Reply with ONLY a "
                          f"JSON object matching this schema: {json.dumps(schema.model_json_schema())[:2500]}")
                continue
            try:
                return schema.model_validate(parsed)
            except ValidationError as exc:
                repair = ("Your JSON violated the schema: "
                          f"{exc.errors()[:5]}. Reply again with ONLY corrected JSON.")
        raise SchemaValidationError(detail_log="structured output failed validation")


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except ValueError:
        try:  # tolerate trailing commas via a cleanup pass
            return json.loads(re.sub(r",\s*([}\]])", r"\1", match.group(0)))
        except ValueError:
            return None


# ---------------------------------------------------------------- fallbacks
class GroqProvider:
    """Optional fast fallback (documented Groq OpenAI-compatible API).
    The configured model is validated against Groq's live /models list; a
    configured-but-missing id falls back to the best available model."""
    name = "groq"
    _PREFERRED = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b",
                  "qwen/qwen3.8-27b", "qwen/qwen3.6-27b", "openai/gpt-oss-20b"]

    def __init__(self) -> None:
        s = get_settings()
        self._model = s.groq_model
        self._client = httpx.AsyncClient(
            base_url="https://api.groq.com/openai/v1",
            headers={"Authorization": f"Bearer {s.groq_api_key}"},
            timeout=httpx.Timeout(60.0, connect=10.0))

    async def _resolve_model(self) -> str:
        try:
            resp = await self._client.get("/models")
            if resp.status_code == 200:
                available = {m["id"] for m in resp.json().get("data", [])}
                if self._model in available:
                    return self._model
                for candidate in self._PREFERRED:
                    if candidate in available:
                        log.warning("groq_model_fallback", extra={"ctx": {
                            "configured": self._model, "using": candidate}})
                        return candidate
                if available:
                    return sorted(available)[0]
        except httpx.HTTPError:
            pass
        return self._model

    async def complete(self, messages, *, model: str, max_tokens=2000,
                       temperature=0.4, student_id=None, request_type="text") -> LLMResult:
        started = time.perf_counter()
        self._model = await self._resolve_model()
        resp = await self._client.post("/chat/completions", json={
            "model": self._model, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature})
        if resp.status_code >= 400:
            raise GenerationError(detail_log=f"groq {resp.status_code}")
        data = resp.json()
        usage = data.get("usage") or {}
        result = LLMResult(content=data["choices"][0]["message"]["content"],
                           model=self._model, provider=self.name,
                           input_tokens=usage.get("prompt_tokens", 0),
                           output_tokens=usage.get("completion_tokens", 0),
                           latency_ms=int((time.perf_counter() - started) * 1000),
                           fallback_used=True)
        from ...services.telemetry import telemetry
        telemetry.record_llm(student_id=student_id, result=result,
                             request_type=request_type, status="ok")
        return result

    async def structured(self, messages, schema: Type[T], *, student_id=None,
                         request_type="structured", max_tokens=4000) -> T:
        """JSON-mode structured generation (documented response_format)."""
        model = await self._resolve_model()
        # NOTE: appended as a *user* note — many providers reject system
        # messages that don't appear at position 0.
        request = messages + [{"role": "user",
                               "content": "Reply with ONLY valid JSON matching this "
                                          f"schema: {json.dumps(schema.model_json_schema())[:2500]}"}]
        resp = await self._client.post("/chat/completions", json={
            "model": model, "messages": request, "max_tokens": max_tokens,
            "temperature": 0.2, "response_format": {"type": "json_object"}})
        if resp.status_code >= 400:
            raise GenerationError(detail_log=f"groq structured {resp.status_code}")
        parsed = _extract_json(resp.json()["choices"][0]["message"]["content"])
        if parsed is None:
            raise SchemaValidationError(detail_log="groq json parse failed")
        try:
            return schema.model_validate(parsed)
        except ValidationError as exc:
            raise SchemaValidationError(detail_log=f"groq schema: {exc.errors()[:4]}") from exc


class OpenAILLMProvider:
    """Optional direct fallback (documented OpenAI chat completions API)."""
    name = "openai"

    def __init__(self) -> None:
        s = get_settings()
        self._client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {s.openai_api_key}"},
            timeout=httpx.Timeout(90.0, connect=15.0))

    async def complete(self, messages, *, model: str, max_tokens=2000,
                       temperature=0.4, student_id=None, request_type="text") -> LLMResult:
        started = time.perf_counter()
        resp = await self._client.post("/chat/completions", json={
            "model": "gpt-4o-mini", "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature})
        if resp.status_code >= 400:
            raise GenerationError(detail_log=f"openai {resp.status_code}")
        data = resp.json()
        usage = data.get("usage") or {}
        result = LLMResult(content=data["choices"][0]["message"]["content"],
                           model="gpt-4o-mini", provider=self.name,
                           input_tokens=usage.get("prompt_tokens", 0),
                           output_tokens=usage.get("completion_tokens", 0),
                           latency_ms=int((time.perf_counter() - started) * 1000),
                           fallback_used=True)
        from ...services.telemetry import telemetry
        telemetry.record_llm(student_id=student_id, result=result,
                             request_type=request_type, status="ok")
        return result


class LLMService:
    """Role-based facade with the configurable fallback chain (#34)."""

    def __init__(self) -> None:
        self._primary: Optional[OpenRouterProvider] = None
        self._fallbacks: list = []

    def _ensure(self):
        if self._primary is None:
            s = get_settings()
            if s.effective_llm_mode == "mock":
                self._primary = MockLLM()
            else:
                self._primary = OpenRouterProvider()
                if s.groq_api_key:
                    self._fallbacks.append(GroqProvider())
                if s.openai_api_key:
                    self._fallbacks.append(OpenAILLMProvider())
        return self._primary

    @property
    def mode(self) -> str:
        return get_settings().effective_llm_mode

    async def complete(self, messages, *, role: str = "content", max_tokens=2000,
                       temperature=0.4, student_id=None, request_type="text") -> LLMResult:
        primary = self._ensure()
        model = await primary.resolve_model(role) if hasattr(primary, "resolve_model") else role
        try:
            return await primary.complete(messages, model=model, max_tokens=max_tokens,
                                          temperature=temperature, student_id=student_id,
                                          request_type=request_type)
        except GenerationError as exc:
            for fallback in self._fallbacks:
                try:
                    log.warning("llm_fallback", extra={"ctx": {
                        "from": "openrouter", "to": fallback.name, "err": str(exc)[:120]}})
                    return await fallback.complete(messages, model=model,
                                                   max_tokens=max_tokens,
                                                   temperature=temperature,
                                                   student_id=student_id,
                                                   request_type=request_type)
                except GenerationError:
                    continue
            raise

    async def structured(self, messages, schema: Type[T], *, student_id=None,
                         request_type="structured", max_tokens=4000) -> T:
        primary = self._ensure()
        if isinstance(primary, MockLLM):
            raise GenerationError("structured generation requires a live provider")
        try:
            return await primary.structured(messages, schema, student_id=student_id,
                                            request_type=request_type,
                                            max_tokens=max_tokens)
        except (GenerationError, SchemaValidationError) as exc:
            for fallback in self._fallbacks:
                if not hasattr(fallback, "structured"):
                    continue
                try:
                    log.warning("structured_fallback", extra={"ctx": {
                        "to": fallback.name, "err": str(exc)[:120]}})
                    return await fallback.structured(
                        messages, schema, student_id=student_id,
                        request_type=request_type, max_tokens=max_tokens)
                except (GenerationError, SchemaValidationError) as exc2:
                    log.warning("structured_fallback_failed", extra={"ctx": {
                        "provider": fallback.name, "err": str(exc2)[:300]}})
                    continue
            raise


llm = LLMService()