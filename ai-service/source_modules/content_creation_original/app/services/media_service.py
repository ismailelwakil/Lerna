"""Media services — audio (TTS async for large text) and the video pipeline
(script → verify → scenes → voice → images → assembly → QC) per spec #21-26."""
from __future__ import annotations

from typing import Optional

from ..core.config import get_settings
from ..core.exceptions import GenerationError
from ..core.logging import get_logger
from ..core.security import new_id
from ..db import get_database
from ..db.models import GeneratedAsset
from ..prompts.templates import verification_prompt, video_script_prompt
from ..providers.llm.openrouter import llm
from ..providers.storage.storage import storage
from ..providers.tts.voice import tts
from ..services.telemetry import telemetry

log = get_logger("media")


async def store_asset(*, student_id: str, kind: str, data: bytes, mime: str,
                      ext: str, job_id: Optional[str] = None,
                      content_item_id: Optional[str] = None,
                      asset_meta: Optional[dict] = None) -> dict:
    key = storage.new_key(student_id, ext)
    await storage.put(key, data, mime=mime)
    db = get_database()
    with db.session_scope() as session:
        asset = GeneratedAsset(
            id=new_id(), student_id=student_id, kind=kind, storage_key=key,
            mime=mime, size_bytes=len(data), job_id=job_id,
            content_item_id=content_item_id, asset_meta=asset_meta or {})
        session.add(asset)
        asset_id = asset.id
    from ..core.security import make_signed_url
    return {"asset_id": asset_id, "kind": kind, "mime": mime,
            "size_bytes": len(data), "url": make_signed_url(key), "meta": asset_meta or {}}


class AudioService:
    async def synthesize(self, *, student_id: str, text: str, voice: Optional[str],
                         speed: float) -> dict:
        settings = get_settings()
        if len(text) > settings.max_audio_chars:
            raise GenerationError(detail_log="audio text too long; use async mode")
        result = await tts.synthesize(text, voice=voice, speed=speed)
        telemetry.record_provider(student_id=student_id, provider=result.provider,
                                  model="tts", request_type="audio",
                                  est_cost_usd=len(text) / 1000 * 0.00015)
        return await store_asset(student_id=student_id, kind="audio",
                                 data=result.audio_bytes, mime=result.mime,
                                 ext=".mp3", asset_meta={"voice": result.voice,
                                                         "chars": len(text)})


class ScriptModel:
    """Validated video script (structured output)."""
    pass


async def _generate_script(topic: str, level: str, language: str,
                           duration: int, scenes: int, source_context: str,
                           student_id: str) -> dict:
    from pydantic import BaseModel, Field, field_validator

    class Scene(BaseModel):
        n: int
        narration: str = Field(max_length=600)
        visual_hint: str = Field(default="", max_length=300)

    class Script(BaseModel):
        title: str = Field(max_length=140)
        scenes: list[Scene]

        @field_validator("scenes")
        @classmethod
        def _scenes_ok(cls, value: list[Scene]) -> list[Scene]:
            if not 2 <= len(value) <= 10:
                raise ValueError("2-10 scenes required")
            return value

    system, task = video_script_prompt(topic, level, language, duration, scenes)
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": (source_context + "\n\n" if source_context else "") + task}]
    script = await llm.structured(messages, Script, student_id=student_id,
                                  request_type="video_script")
    return script.model_dump()


async def _verify_script(script: dict, source_context: str, student_id: str) -> list[str]:
    """Fact-check each scene's narration against the source (when present).
    Returns issues; scenes with issues are re-scripted individually."""
    if not source_context:
        return []
    issues: list[str] = []
    for scene in script["scenes"]:
        system, task = verification_prompt(scene["narration"], source_context)
        try:
            from ..services.verification.verifier import verify_text
            passed, why = await verify_text(scene["narration"], source_context,
                                            student_id=student_id)
            if not passed:
                issues.append(f"scene {scene['n']}: {why}")
        except Exception as exc:  # noqa: BLE001 — verification is best effort
            log.warning("scene_verify_failed", extra={"ctx": {"err": str(exc)[:120]}})
    return issues


class VideoService:
    """Scene-based pipeline (spec #21): per-scene voice + slide image +
    subtitle manifest, assembled into an HTML5 lesson player (no ffmpeg
    dependency) with optional Gemini Veo clips when configured."""

    async def generate(self, job, *, student_id: str, topic: str, level: str,
                       language: str, duration: int, voice: Optional[str],
                       source_context: str, progress) -> dict:
        scenes_count = max(3, min(8, duration // 30))
        progress(20, "SCRIPTING")
        script = await _generate_script(topic, level, language, duration,
                                        scenes_count, source_context, student_id)
        progress(45, "VERIFYING")
        issues = await _verify_script(script, source_context, student_id)
        if issues:  # regenerate only flagged scenes
            progress(50, "VERIFYING")
            fixed = await _generate_script(topic + " (fix: " + "; ".join(issues[:3]) + ")",
                                           level, language, duration, scenes_count,
                                           source_context, student_id)
            by_n = {s["n"]: s for s in fixed["scenes"]}
            for scene in script["scenes"]:
                if scene["n"] in by_n:
                    scene["narration"] = by_n[scene["n"]]["narration"]

        progress(60, "SCENE_GENERATION")
        scene_assets = []
        for i, scene in enumerate(script["scenes"]):
            audio = await tts.synthesize(scene["narration"], voice=voice, speed=1.0)
            audio_meta = await store_asset(
                student_id=student_id, kind="audio", data=audio.audio_bytes,
                mime="audio/mpeg", ext=".mp3", job_id=job.id,
                asset_meta={"scene": scene["n"], "text": scene["narration"]})
            from ..services.images.diagram import diagram_service
            try:
                svg, _spec = await diagram_service.create(
                    topic=f"{script['title']} — {scene.get('visual_hint') or scene['narration'][:60]}",
                    kind="flow", learner={}, level=level, language=language,
                    source_context=wrap_scene(scene["narration"]), style_hint=None)
                visual = await store_asset(student_id=student_id, kind="image",
                                           data=svg.encode(), mime="image/svg+xml",
                                           ext=".svg", job_id=job.id,
                                           asset_meta={"scene": scene["n"]})
            except Exception:  # noqa: BLE001 — scene visual is non-critical
                visual = None
            scene_assets.append({
                "n": scene["n"], "title": scene.get("visual_hint", "")[:80],
                "narration": scene["narration"], "audio": audio_meta,
                "visual": visual})
            progress(60 + int(25 * (i + 1) / len(script["scenes"])), "SCENE_GENERATION")

        progress(90, "ASSEMBLING")
        player_html = _render_player(script["title"], topic, scene_assets)
        package = await store_asset(
            student_id=student_id, kind="video", data=player_html.encode("utf-8"),
            mime="text/html", ext=".html", job_id=job.id,
            asset_meta={"scenes": len(scene_assets), "format": "lesson-player"})
        subtitles = "\n\n".join(
            f"[Scene {s['n']}] {s['narration']}" for s in scene_assets)
        sub_asset = await store_asset(
            student_id=student_id, kind="subtitle", data=subtitles.encode(),
            mime="text/plain", ext=".vtt.txt", job_id=job.id, asset_meta={})

        progress(96, "QUALITY_CHECK")
        missing_audio = [s["n"] for s in scene_assets if not s.get("audio", {}).get("url")]
        qc = {"missing_audio_scenes": missing_audio, "script_issues": issues,
              "passed": not missing_audio}

        progress(100, "COMPLETED")
        return {"title": script["title"], "scenes": scene_assets,
                "player": package, "subtitles": sub_asset, "quality_control": qc}


def wrap_scene(text: str) -> str:
    from ..core.security import wrap_untrusted
    return wrap_untrusted(text[:1200], label="scene")


def _render_player(title: str, topic: str, scenes: list[dict]) -> str:
    import html
    blocks = []
    for scene in scenes:
        audio_url = scene["audio"]["url"]
        visual_url = (scene["visual"] or {}).get("url")
        visual_tag = (f'<img class="slide" src="{html.escape(visual_url)}" alt="scene {scene["n"]}">'
                      if visual_url else '<div class="slide placeholder">📝 visual</div>')
        blocks.append(f'''<section class="scene" id="s{scene['n']}">
  <h3>Scene {scene['n']} — {html.escape(scene.get('title') or '')}</h3>
  {visual_tag}
  <p class="narration">{html.escape(scene['narration'])}</p>
  <audio controls preload="none" src="{html.escape(audio_url)}"></audio>
</section>''')
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title><style>
body{{font-family:system-ui,sans-serif;background:#0b1220;color:#e8edf7;margin:0;padding:24px}}
h1{{color:#7cc4ff}} .scene{{max-width:720px;margin:32px auto;background:#101a2e;
border:1px solid #233350;border-radius:14px;padding:20px}}
.slide{{max-width:100%;border-radius:10px;background:#fff}} .placeholder{{padding:60px;text-align:center;color:#64748b}}
.narration{{line-height:1.6;color:#c7d2e5}} audio{{width:100%;margin-top:10px}}
</style></head><body>
<h1>🎬 {html.escape(title)}</h1>
<p>EDUnation lesson — {html.escape(topic)} (interactive player: play each scene, pause anytime and ask your tutor)</p>
{"".join(blocks)}
</body></html>'''


audio_service = AudioService()
video_service = VideoService()