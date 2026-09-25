"""Provider interfaces (spec #3). External services are NEVER called from routes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable



@dataclass
class LLMResult:
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    est_cost_usd: float = 0.0
    latency_ms: int = 0
    fallback_used: bool = False


@dataclass
class Embedded:
    vector: list[float]
    provider: str
    model: str


@dataclass
class ImageResult:
    image_bytes: bytes
    mime: str
    provider: str
    model: str


@dataclass
class VideoResult:
    video_bytes: Optional[bytes]
    mime: str
    provider: str
    model: str
    external_uri: Optional[str] = None


@dataclass
class AudioResult:
    audio_bytes: bytes
    mime: str
    provider: str
    voice: str


@dataclass
class Transcript:
    text: str
    provider: str
    model: str
    language: Optional[str] = None


@runtime_checkable
class LLMProvider(Protocol):
    name: str
    async def complete(self, messages: list[dict], *, model: str,
                       max_tokens: int, temperature: float,
                       student_id: Optional[str], request_type: str) -> LLMResult: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    name: str
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class ImageGenerationProvider(Protocol):
    name: str
    async def generate(self, prompt: str, *, aspect: str = "16:9") -> ImageResult: ...


@runtime_checkable
class VideoGenerationProvider(Protocol):
    name: str
    async def generate(self, prompt: str, *, seconds: int = 8) -> VideoResult: ...


@runtime_checkable
class TextToSpeechProvider(Protocol):
    name: str
    async def synthesize(self, text: str, *, voice: Optional[str],
                         speed: float = 1.0) -> AudioResult: ...


@runtime_checkable
class SpeechToTextProvider(Protocol):
    name: str
    async def transcribe(self, audio: bytes, *, mime: str,
                         language: str = "multi") -> Transcript: ...


@dataclass
class ScoredPoint:
    score: float
    payload: dict


@runtime_checkable
class VectorStoreProvider(Protocol):
    name: str
    async def ensure_collection(self, dim: int) -> None: ...
    async def upsert(self, ids: list[str], vectors: list[list[float]],
                     payloads: list[dict]) -> None: ...
    async def search(self, vector: list[float], *, k: int = 5,
                     filter_student: Optional[str] = None,
                     filter_document: Optional[str] = None) -> list[ScoredPoint]: ...
    async def delete_document(self, document_id: str) -> None: ...


@runtime_checkable
class StorageProvider(Protocol):
    name: str
    async def put(self, key: str, data: bytes, *, mime: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...


@runtime_checkable
class ObservabilityProvider(Protocol):
    name: str
    def track_generation(self, *, request_id: str, student_id: Optional[str],
                         provider: str, model: str, request_type: str,
                         input_tokens: int, output_tokens: int,
                         est_cost_usd: float, latency_ms: int, status: str,
                         metadata: Optional[dict] = None) -> None: ...