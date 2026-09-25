"""Gemini multimodal provider — embeddings, images, video (spec #20, #21).

All calls use Google's documented generativelanguage REST API with the
configured GEMINI_API_KEY. Every feature degrades gracefully to
*_PROVIDER_UNAVAILABLE when the key/model is missing (spec #48)."""
from __future__ import annotations

import asyncio
import base64
import time
from typing import Optional

import httpx

from ...core.config import get_settings
from ...core.exceptions import ProviderUnavailableError
from ...core.logging import get_logger
from ..base import AudioResult  # noqa: F401 (re-export convenience)
from ..base import ImageResult, VideoResult

log = get_logger("gemini")


class GeminiClient:
    name = "gemini"

    def __init__(self) -> None:
        s = get_settings()
        if not s.gemini_api_key:
            raise ProviderUnavailableError("Gemini is not configured.",
                                           code="GEMINI_UNAVAILABLE")
        self._settings = s
        self._client = httpx.AsyncClient(
            base_url=s.gemini_base, headers={"x-goog-api-key": s.gemini_api_key},
            timeout=httpx.Timeout(240.0, connect=15.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    # ---------------------------------------------------------- embeddings
    async def embed(self, texts: list[str]) -> list[list[float]]:
        s = self._settings
        vectors: list[list[float]] = []
        for text in texts:  # documented per-request API; keep rate friendly
            resp = await self._client.post(
                f"/models/{s.gemini_embedding_model}:embedContent", json={
                    "content": {"parts": [{"text": text[:8000]}]},
                    "outputDimensionality": s.gemini_embedding_dim})
            if resp.status_code >= 400:
                raise ProviderUnavailableError(
                    f"Embedding failed ({resp.status_code}).",
                    code="EMBEDDING_PROVIDER_UNAVAILABLE")
            vectors.append([float(x) for x in resp.json()["embedding"]["values"]])
            await asyncio.sleep(0.02)
        return vectors


class GeminiEmbedding:
    """Embedding facade with honest local fallback (hashed, 384-dim) so RAG
    works offline; the dim is recorded per-collection to avoid mismatches."""
    name = "gemini-embedding"

    def __init__(self) -> None:
        self._client: Optional[GeminiClient] = None
        self._dim: Optional[int] = None

    async def _ensure(self) -> Optional[GeminiClient]:
        if self._client is None:
            try:
                self._client = GeminiClient()
            except ProviderUnavailableError:
                return None
        return self._client

    @property
    def dim(self) -> int:
        return self._dim or get_settings().gemini_embedding_dim

    async def embed(self, texts: list[str]) -> tuple[list[list[float]], str, int]:
        """Returns (vectors, provider_name, dim)."""
        client = await self._ensure()
        if client is not None:
            try:
                vectors = await client.embed(texts)
                self._dim = len(vectors[0]) if vectors else None
                return vectors, "gemini", self._dim or get_settings().gemini_embedding_dim
            except ProviderUnavailableError as exc:
                log.warning("embedding_fallback_local", extra={"ctx": {"err": str(exc)[:120]}})
        from ...services.rag.local_embed import hash_embed_many
        return hash_embed_many(texts), "local-hash", 384


class GeminiImageProvider:
    """Image generation via Gemini image models (documented generateContent API
    with image response modality)."""
    name = "gemini-image"

    def __init__(self) -> None:
        self._client: Optional[GeminiClient] = None

    async def _ensure(self) -> GeminiClient:
        if self._client is None:
            self._client = GeminiClient()  # raises gracefully if unconfigured
        return self._client

    async def generate(self, prompt: str, *, aspect: str = "16:9") -> ImageResult:
        s = get_settings()
        client = await self._ensure()
        resp = await client._client.post(  # noqa: SLF001 — same-package client
            f"/models/{s.gemini_image_model}:generateContent", json={
                "contents": [{"parts": [{"text": prompt[:2000]}]}],
                "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}})
        if resp.status_code >= 400:
            raise ProviderUnavailableError(
                f"Image generation failed ({resp.status_code}).",
                code="IMAGE_PROVIDER_UNAVAILABLE")
        data = resp.json()
        for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline:
                return ImageResult(
                    image_bytes=base64.b64decode(inline["data"]),
                    mime=inline.get("mimeType") or inline.get("mime_type", "image/png"),
                    provider=self.name, model=s.gemini_image_model)
        raise ProviderUnavailableError("Image model returned no image.",
                                       code="IMAGE_PROVIDER_UNAVAILABLE")


class GeminiVideoProvider:
    """Short clip generation via Gemini Veo (predictLongRunning + polling)."""
    name = "gemini-video"

    def __init__(self) -> None:
        self._client: Optional[GeminiClient] = None

    async def _ensure(self) -> GeminiClient:
        if self._client is None:
            self._client = GeminiClient()
        return self._client

    async def generate(self, prompt: str, *, seconds: int = 8) -> VideoResult:
        s = get_settings()
        client = await self._ensure()
        start = await client._client.post(  # noqa: SLF001
            f"/models/{s.gemini_video_model}:predictLongRunning", json={
                "instances": [{"prompt": prompt[:1500]}],
                "parameters": {"durationSeconds": max(4, min(seconds, 8))}})
        if start.status_code >= 400:
            raise ProviderUnavailableError(
                f"Video model unavailable ({start.status_code}).",
                code="VIDEO_PROVIDER_UNAVAILABLE")
        operation = start.json().get("name", "")
        deadline = time.time() + 540  # 9 minutes max
        while time.time() < deadline:
            poll = await client._client.get(f"/{operation}")  # noqa: SLF001
            if poll.status_code == 200:
                body = poll.json()
                if body.get("done"):
                    uri = _dig_video_uri(body)
                    if not uri:
                        raise ProviderUnavailableError("Video operation produced no file.",
                                                       code="VIDEO_PROVIDER_UNAVAILABLE")
                    video = await client._client.get(uri)  # noqa: SLF001
                    return VideoResult(video_bytes=video.content if video.status_code == 200 else None,
                                       mime="video/mp4", provider=self.name,
                                       model=s.gemini_video_model, external_uri=uri)
            await asyncio.sleep(8)
        raise ProviderUnavailableError("Video generation timed out.",
                                       code="VIDEO_PROVIDER_UNAVAILABLE")


def _dig_video_uri(body: dict) -> Optional[str]:
    import json as _json
    text = _json.dumps(body)
    import re
    match = re.search(r"https://[^\"]+?\.(?:mp4|mov)[^\"]*", text)
    return match.group(0).replace("\\u003d", "=").replace("\\u0026", "&") if match else None