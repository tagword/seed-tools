"""Audio/video analysis tools (tool-first multimodal)."""

from __future__ import annotations

import contextlib
import json
import logging
import mimetypes
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, List, Optional, Tuple

import requests

from seed.core import env_access as _ea
from seed.core.models import Tool
from seed_tools.artifact_helpers import _artifact_summary, _artifact_write_text
from seed_tools.shell_helpers import _active_agent_and_session, _env_truthy

logger = logging.getLogger(__name__)


def _resolve_attachment_path(attachment_id: str) -> Tuple[str, Path]:
    from seed.core.media_store import resolve_session_media_path

    aid = (attachment_id or "").strip()
    if not aid:
        raise ValueError("attachment_id required")
    agent_id, session_id = _active_agent_and_session()
    p = resolve_session_media_path(agent_id, session_id, aid)
    if not p or not p.is_file():
        raise ValueError(f"attachment not found: {aid}")
    return aid, p


def _transcriptions_url(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if base.endswith("/audio/transcriptions"):
        return base
    return f"{base}/audio/transcriptions"


def _auth_headers(preset: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    key = str(preset.get("api_key") or "").strip()
    scheme = str(preset.get("auth_scheme") or "Bearer").strip() or "Bearer"
    if key:
        headers["Authorization"] = f"{scheme} {key}"
    return headers


def call_audio_transcription(
    preset: dict[str, Any],
    path: Path,
    *,
    language: str = "",
    prompt: str = "",
) -> str:
    model = str(preset.get("model") or "").strip()
    if not model:
        raise ValueError("audio preset missing model (e.g. whisper-1)")

    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "application/octet-stream"
    url = _transcriptions_url(str(preset.get("base_url") or ""))
    timeout = _ea.pick_int(300, *_ea.AUDIO_TRANSCRIBE_TIMEOUT_SEC)

    data: dict[str, str] = {"model": model, "response_format": "json"}
    if language.strip():
        data["language"] = language.strip()
    if prompt.strip():
        data["prompt"] = prompt.strip()

    with path.open("rb") as fh:
        files = {"file": (path.name, fh, mime)}
        resp = requests.post(
            url,
            headers=_auth_headers(preset),
            data=data,
            files=files,
            timeout=max(30, timeout),
        )
    if resp.status_code >= 400:
        detail = resp.text[:500]
        try:
            err = resp.json().get("error", detail)
            if isinstance(err, dict):
                detail = err.get("message") or str(err)
        except Exception:
            pass
        raise ValueError(f"audio transcription failed ({resp.status_code}): {detail}")

    try:
        payload = resp.json()
        text = str(payload.get("text") or "").strip()
    except Exception:
        text = (resp.text or "").strip()
    if not text:
        raise ValueError("empty transcription result")
    return text


def _video_max_frames() -> int:
    try:
        return max(1, min(_ea.pick_int(8, *_ea.VIDEO_MAX_FRAMES), 16))
    except ValueError:
        return 8


def _video_frame_interval() -> float:
    try:
        return max(0.5, float(_ea.pick_default("2", *_ea.VIDEO_FRAME_INTERVAL_SEC)))
    except ValueError:
        return 2.0


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg"))


def extract_video_frames(path: Path, *, max_frames: int, interval_sec: float) -> List[Path]:
    if not _ffmpeg_available():
        raise ValueError(
            "ffmpeg not found; install ffmpeg or upload screenshots for vision_analyze"
        )
    tmp = Path(tempfile.mkdtemp(prefix="codeagent-vframes-"))
    pattern = str(tmp / "frame_%03d.jpg")
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(path),
        "-vf",
        f"fps=1/{interval_sec}",
        "-frames:v",
        str(max_frames),
        pattern,
    ]
    try:
        subprocess.run(cmd, check=True, timeout=180, capture_output=True)
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode("utf-8", errors="replace")[:400]
        raise ValueError(f"ffmpeg frame extract failed: {err or e}") from e
    except subprocess.TimeoutExpired as e:
        raise ValueError("ffmpeg frame extract timed out") from e
    frames = sorted(tmp.glob("frame_*.jpg"))
    if not frames:
        raise ValueError("no frames extracted from video")
    return frames[:max_frames]


def extract_video_audio(path: Path) -> Optional[Path]:
    if not _ffmpeg_available():
        return None
    tmp = Path(tempfile.mktemp(suffix=".m4a", prefix="codeagent-vaudio-"))
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(path),
        "-vn",
        "-acodec",
        "aac",
        "-b:a",
        "128k",
        str(tmp),
    ]
    try:
        subprocess.run(cmd, check=True, timeout=120, capture_output=True)
    except Exception:
        with contextlib.suppress(Exception):
            tmp.unlink(missing_ok=True)
        return None
    if tmp.is_file() and tmp.stat().st_size > 0:
        return tmp
    with contextlib.suppress(Exception):
        tmp.unlink(missing_ok=True)
    return None


def _maybe_artifact(text: str, *, kind: str, title: str) -> tuple[str, Optional[str]]:
    try:
        max_inline = _ea.pick_int(12000, *_ea.MEDIA_RESULT_MAX_CHARS)
    except ValueError:
        max_inline = 12000
    if len(text) <= max_inline or not _env_truthy("SEED_TOOL_ARTIFACTS", "1"):
        return text, None
    ap = _artifact_write_text(kind=kind, name_hint=kind, text=text)
    if not ap:
        return text[:max_inline], None
    summary = _artifact_summary(title=title, text=text, path=ap)
    return summary, ap


async def audio_transcribe(
    attachment_id: str = "",
    language: str = "",
    prompt: str = "",
) -> str:
    """Transcribe an audio attachment using the configured audio preset (Whisper-compatible API)."""
    try:
        aid, path = _resolve_attachment_path(attachment_id)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    mime, _ = mimetypes.guess_type(str(path))
    if mime and not mime.startswith("audio/") and not path.suffix.lower() in (
        ".mp3",
        ".wav",
        ".m4a",
        ".ogg",
        ".flac",
        ".webm",
    ):
        return json.dumps(
            {"error": f"not an audio attachment: {path.name}"},
            ensure_ascii=False,
        )

    try:
        from seed.core.agent_context import get_active_audio_preset
        from seed_tools._preset_helpers import resolve_capability_preset

        preset = resolve_capability_preset(
            "supports_audio",
            "CODEAGENT_AUDIO_PRESET_ID",
            get_active_audio_preset,
            "audio transcription",
        )
        text = call_audio_transcription(
            preset,
            path,
            language=language,
            prompt=prompt,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    summary, artifact_path = _maybe_artifact(
        text,
        kind="audio_transcribe",
        title="[audio_transcribe]",
    )
    payload: dict[str, Any] = {
        "attachment_id": aid,
        "transcript": text,
        "summary": summary,
        "model": preset.get("model"),
    }
    if artifact_path:
        payload["artifact_path"] = artifact_path
    return json.dumps(payload, ensure_ascii=False)


async def video_analyze(
    attachment_id: str = "",
    query: str = "",
    max_frames: int = 0,
    interval_sec: float = 0,
    include_audio: bool = True,
) -> str:
    """Analyze a video attachment: extract frames (ffmpeg) + optional audio transcript + vision summary."""
    try:
        aid, path = _resolve_attachment_path(attachment_id)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    mime, _ = mimetypes.guess_type(str(path))
    if mime and not mime.startswith("video/") and path.suffix.lower() not in (
        ".mp4",
        ".webm",
        ".mov",
        ".mkv",
        ".avi",
    ):
        return json.dumps({"error": f"not a video attachment: {path.name}"}, ensure_ascii=False)

    mf = max_frames or _video_max_frames()
    mf = max(1, min(int(mf), _video_max_frames()))
    interval = interval_sec or _video_frame_interval()
    interval = max(0.5, float(interval))

    audio_transcript = ""
    if include_audio:
        audio_path = extract_video_audio(path)
        if audio_path:
            try:
                from seed.core.agent_context import get_active_audio_preset
                from seed_tools._preset_helpers import resolve_capability_preset

                apreset = resolve_capability_preset(
                    "supports_audio",
                    "CODEAGENT_AUDIO_PRESET_ID",
                    get_active_audio_preset,
                    "audio transcription",
                )
                audio_transcript = call_audio_transcription(apreset, audio_path)
            except Exception as ex:
                audio_transcript = f"[audio track unavailable: {ex}]"
            finally:
                with contextlib.suppress(Exception):
                    audio_path.unlink(missing_ok=True)

    try:
        frames = extract_video_frames(path, max_frames=mf, interval_sec=interval)
    except ValueError as e:
        payload = {"error": str(e), "attachment_id": aid}
        if audio_transcript:
            payload["audio_transcript"] = audio_transcript
        return json.dumps(payload, ensure_ascii=False)

    from seed_tools.vision import _build_vision_prompt, _call_vision_llm

    frame_pairs = [(f"frame-{i+1}", p) for i, p in enumerate(frames)]
    bs = 4
    visual_parts: List[str] = []
    for i in range(0, len(frame_pairs), bs):
        batch = frame_pairs[i : i + bs]
        vprompt = _build_vision_prompt(
            query or "Describe what happens in this video segment.",
            "",
            "detailed",
            len(batch),
        )
        if audio_transcript:
            vprompt += f"\n\nAudio transcript (if relevant):\n{audio_transcript[:4000]}"
        try:
            result = _call_vision_llm(batch, vprompt)
            if isinstance(result, tuple):
                vtext, _usage = result
            else:
                vtext = str(result)
            visual_parts.append(vtext)
        except Exception as ex:
            visual_parts.append(f"[vision error: {ex}]")

    visual_summary = "\n\n---\n\n".join(visual_parts).strip()
    combined = visual_summary
    if audio_transcript:
        combined = f"**Visual**\n{visual_summary}\n\n**Audio transcript**\n{audio_transcript}"

    summary, artifact_path = _maybe_artifact(
        combined,
        kind="video_analyze",
        title="[video_analyze]",
    )

    with contextlib.suppress(Exception):
        for fp in frames:
            fp.unlink(missing_ok=True)
        if frames:
            frames[0].parent.rmdir()

    payload: dict[str, Any] = {
        "attachment_id": aid,
        "frame_count": len(frame_pairs),
        "visual_summary": visual_summary,
        "audio_transcript": audio_transcript or None,
        "summary": summary,
    }
    if artifact_path:
        payload["artifact_path"] = artifact_path
    return json.dumps(payload, ensure_ascii=False)


audio_transcribe_def = Tool(
    name="audio_transcribe",
    description=(
        "Transcribe speech from an audio attachment (OpenAI-compatible /audio/transcriptions, e.g. whisper-1). "
        "Use when the user uploads audio or asks what was said in a recording."
    ),
    parameters={
        "attachment_id": {"type": "string", "required": True, "description": "Audio attachment id"},
        "language": {
            "type": "string",
            "required": False,
            "description": "ISO language hint, e.g. zh, en",
        },
        "prompt": {
            "type": "string",
            "required": False,
            "description": "Optional prompt to guide transcription vocabulary",
        },
    },
    returns="JSON with transcript text",
    category="vision",
)

async def attachment_resolve_path(attachment_id: str) -> str:
    """Return absolute filesystem path for an attachment (e.g. MiniMax MCP image_url)."""
    try:
        aid, path = _resolve_attachment_path(attachment_id)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    return json.dumps(
        {"attachment_id": aid, "path": str(path.resolve()), "filename": path.name},
        ensure_ascii=False,
    )


attachment_resolve_path_def = Tool(
    name="attachment_resolve_path",
    description=(
        "Resolve an attachment id to its absolute file path on disk. "
        "Use before MiniMax MCP understand_image (image_url) or other local-path tools."
    ),
    parameters={
        "attachment_id": {"type": "string", "required": True, "description": "Attachment id from [attachment:...]"},
    },
    returns="JSON with path",
    category="vision",
)


video_analyze_def = Tool(
    name="video_analyze",
    description=(
        "Analyze a video attachment: extracts key frames (requires ffmpeg on server), "
        "optionally transcribes audio track, and summarizes with the vision model. "
        "Use when user message contains a video attachment."
    ),
    parameters={
        "attachment_id": {"type": "string", "required": True, "description": "Video attachment id"},
        "query": {"type": "string", "required": False, "description": "What to focus on in the video"},
        "max_frames": {
            "type": "integer",
            "required": False,
            "description": "Max frames to sample (default from env, max 16)",
        },
        "interval_sec": {
            "type": "number",
            "required": False,
            "description": "Seconds between sampled frames",
        },
        "include_audio": {
            "type": "boolean",
            "required": False,
            "description": "Also transcribe audio track if present",
            "default": True,
        },
    },
    returns="JSON with visual_summary and optional audio_transcript",
    category="vision",
)
