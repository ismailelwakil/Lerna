"""Voice providers — TTS (ElevenLabs → OpenAI fallback) and STT
(Deepgram → OpenAI fallback), per spec #24, #25, #34."""
from __future__ import annotations

from typing import Optional

import httpx

from ...core.config import get_settings
from ...core.exceptions import ProviderUnavailableError
from ...core.logging import get_logger
from ..base import AudioResult, Transcript

log = get_logger("voice")


class ElevenLabsTTS:
    """Documented ElevenLabs API: POST /v1/text-to-speech/{voice_id}
    with multilingual v2 (English + Arabic support)."""
    name = "elevenlabs"

    async def synthesize(self, text: str, *, voice: Optional[str] = None,
                         speed: float = 1.0) -> AudioResult:
        s = get_settings()
        if not s.elevenlabs_api_key:
            raise ProviderUnavailableError("ElevenLabs not configured.",
                                           code="TTS_PROVIDER_UNAVAILABLE")
        voice_id = voice or s.elevenlabs_voice_id
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=15.0)) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                params={"output_format": "mp3_44100_128"},
                headers={"xi-api-key": s.elevenlabs_api_key},
                json={"text": text[: get_settings().max_audio_chars],
                      "model_id": "eleven_multilingual_v2",
                      "voice_settings": {"stability": 0.5, "similarity_boost": 0.75,
                                         "speed": max(0.7, min(1.2, speed))}})
        if resp.status_code >= 400:
            raise ProviderUnavailableError(
                f"ElevenLabs failed ({resp.status_code}).", code="TTS_PROVIDER_UNAVAILABLE")
        return AudioResult(audio_bytes=resp.content, mime="audio/mpeg",
                           provider=self.name, voice=voice_id)


class OpenAITTS:
    """Fallback TTS — documented /v1/audio/speech."""
    name = "openai-tts"

    async def synthesize(self, text: str, *, voice: Optional[str] = None,
                         speed: float = 1.0) -> AudioResult:
        s = get_settings()
        if not s.openai_api_key:
            raise ProviderUnavailableError("OpenAI TTS not configured.",
                                           code="TTS_PROVIDER_UNAVAILABLE")
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=15.0)) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {s.openai_api_key}"},
                json={"model": "gpt-4o-mini-tts", "voice": voice or "alloy",
                      "input": text[: s.max_audio_chars], "speed": speed,
                      "response_format": "mp3"})
        if resp.status_code >= 400:
            raise ProviderUnavailableError(
                f"OpenAI TTS failed ({resp.status_code}).", code="TTS_PROVIDER_UNAVAILABLE")
        return AudioResult(audio_bytes=resp.content, mime="audio/mpeg",
                           provider=self.name, voice=voice or "alloy")


class TTSService:
    """ElevenLabs → OpenAI fallback chain."""

    def __init__(self) -> None:
        self._providers: list = []

    async def synthesize(self, text: str, *, voice: Optional[str] = None,
                         speed: float = 1.0) -> AudioResult:
        s = get_settings()
        providers: list = []
        if s.elevenlabs_api_key:
            providers.append(ElevenLabsTTS())
        if s.openai_api_key:
            providers.append(OpenAITTS())
        if not providers:
            raise ProviderUnavailableError("No text-to-speech provider configured.",
                                           code="TTS_PROVIDER_UNAVAILABLE")
        last: Optional[ProviderUnavailableError] = None
        for provider in providers:
            try:
                return await provider.synthesize(text, voice=voice, speed=speed)
            except ProviderUnavailableError as exc:
                last = exc
                log.warning("tts_fallback", extra={"ctx": {"provider": provider.name}})
        raise last


class DeepgramSTT:
    """Documented Deepgram /v1/listen (nova-3, multi-language incl. Arabic)."""
    name = "deepgram"

    async def transcribe(self, audio: bytes, *, mime: str = "audio/webm",
                         language: str = "multi") -> Transcript:
        s = get_settings()
        if not s.deepgram_api_key:
            raise ProviderUnavailableError("Deepgram not configured.",
                                           code="STT_PROVIDER_UNAVAILABLE")
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
            resp = await client.post(
                "https://api.deepgram.com/v1/listen",
                params={"model": "nova-3", "language": language, "punctuate": "true",
                        "smart_format": "true"},
                headers={"Authorization": f"Token {s.deepgram_api_key}",
                         "Content-Type": mime},
                content=audio)
        if resp.status_code >= 400:
            raise ProviderUnavailableError(
                f"Deepgram failed ({resp.status_code}).", code="STT_PROVIDER_UNAVAILABLE")
        result = resp.json()["results"]["channels"][0]["alternatives"][0]
        return Transcript(text=result.get("transcript", ""), provider=self.name,
                          model="nova-3", language=language)


class OpenAISTT:
    """Fallback STT — documented /v1/audio/transcriptions (whisper-1)."""
    name = "openai-stt"

    async def transcribe(self, audio: bytes, *, mime: str = "audio/webm",
                         language: str = "multi") -> Transcript:
        s = get_settings()
        if not s.openai_api_key:
            raise ProviderUnavailableError("OpenAI STT not configured.",
                                           code="STT_PROVIDER_UNAVAILABLE")
        detected = None if language == "multi" else language
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {s.openai_api_key}"},
                files={"file": ("audio", audio, mime)},
                data={"model": "whisper-1", **({"language": detected} if detected else {})})
        if resp.status_code >= 400:
            raise ProviderUnavailableError(
                f"OpenAI STT failed ({resp.status_code}).", code="STT_PROVIDER_UNAVAILABLE")
        return Transcript(text=resp.json().get("text", ""), provider=self.name,
                          model="whisper-1", language=detected)


class STTService:
    async def transcribe(self, audio: bytes, *, mime: str = "audio/webm",
                         language: str = "multi") -> Transcript:
        s = get_settings()
        providers: list = []
        if s.deepgram_api_key:
            providers.append(DeepgramSTT())
        if s.openai_api_key:
            providers.append(OpenAISTT())
        if not providers:
            raise ProviderUnavailableError("No speech-to-text provider configured.",
                                           code="STT_PROVIDER_UNAVAILABLE")
        last: Optional[ProviderUnavailableError] = None
        for provider in providers:
            try:
                return await provider.transcribe(audio, mime=mime, language=language)
            except ProviderUnavailableError as exc:
                last = exc
                log.warning("stt_fallback", extra={"ctx": {"provider": provider.name}})
        raise last


tts = TTSService()
stt = STTService()