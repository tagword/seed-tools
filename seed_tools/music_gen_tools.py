"""Music generation tool (MiniMax music_generation API)."""

from __future__ import annotations

import base64
import json
import logging
import uuid
from pathlib import Path
from typing import Any, List, Optional

from seed.core.models import Tool
from seed_tools.shell_helpers import _active_agent_and_session

logger = logging.getLogger(__name__)


def _attachment_to_audio_base64(path: Path) -> str:
    raw = path.read_bytes()
    if len(raw) > 50 * 1024 * 1024:
        raise ValueError(f"reference audio too large (max 50MB): {path.name}")
    return base64.standard_b64encode(raw).decode("ascii")


def collect_reference_audio(
    *,
    audio_url: str = "",
    attachment_ids: Optional[List[str]] = None,
) -> tuple[str, str]:
    """Return (audio_url, audio_base64) — at most one set."""
    url = (audio_url or "").strip()
    if url:
        return url, ""
    ids: List[str] = []
    if attachment_ids:
        ids.extend(str(x).strip() for x in attachment_ids if str(x).strip())
    if not ids:
        return "", ""
    if len(ids) > 1:
        raise ValueError("music cover supports one reference audio attachment at a time")
    from codeagent.core.attachments import resolve_attachment_path

    agent_id, session_id = _active_agent_and_session()
    p = resolve_attachment_path(agent_id, session_id, ids[0])
    if not p or not p.is_file():
        raise ValueError(f"reference attachment not found: {ids[0]}")
    return "", _attachment_to_audio_base64(p)


async def music_generate(
    prompt: str = "",
    lyrics: str = "",
    is_instrumental: bool = False,
    lyrics_optimizer: bool = False,
    audio_url: str = "",
    attachment_ids: Optional[List[str]] = None,
    cover_feature_id: str = "",
) -> str:
    """Generate a song via configured music preset; saves MP3 as session attachment."""
    style = (prompt or "").strip()
    song_lyrics = (lyrics or "").strip()
    if not style and not song_lyrics and not lyrics_optimizer and not is_instrumental:
        return json.dumps({"error": "prompt or lyrics required"}, ensure_ascii=False)

    try:
        from codeagent.core.music_models import resolve_music_preset
        from seed.core.agent_context import get_active_music_preset
        from seed.core.model_providers import call_music_generations, resolve_provider_for_preset

        preset = resolve_music_preset(get_active_music_preset() or None)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    try:
        ref_url, ref_b64 = collect_reference_audio(
            audio_url=audio_url,
            attachment_ids=attachment_ids,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    try:
        audio_bytes, mime, meta = call_music_generations(
            preset,
            prompt=style,
            lyrics=song_lyrics,
            is_instrumental=bool(is_instrumental),
            lyrics_optimizer=bool(lyrics_optimizer),
            audio_url=ref_url,
            audio_base64=ref_b64,
            cover_feature_id=(cover_feature_id or "").strip(),
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    ext = "mp3"
    if mime == "audio/wav":
        ext = "wav"
    elif mime == "audio/pcm":
        ext = "pcm"

    agent_id, session_id = _active_agent_and_session()
    from codeagent.core.attachments import save_attachment

    fname = f"generated-music-{uuid.uuid4().hex[:8]}.{ext}"
    try:
        saved = save_attachment(
            agent_id=agent_id,
            session_id=session_id,
            raw_bytes=audio_bytes,
            filename=fname,
            mime=mime,
        )
    except Exception as e:
        logger.warning("save generated music failed: %s", e)
        return json.dumps({"error": "failed to save generated music"}, ensure_ascii=False)

    payload: dict[str, Any] = {
        "prompt": style,
        "lyrics": song_lyrics[:200] + ("…" if len(song_lyrics) > 200 else ""),
        "model": preset.get("model"),
        "provider": resolve_provider_for_preset(preset),
        "is_instrumental": bool(is_instrumental),
        "lyrics_optimizer": bool(lyrics_optimizer),
        "audio": {
            "attachment_id": saved.id,
            "filename": saved.filename,
            "url": f"/api/attachments/{saved.id}?session_id={session_id}&agent_id={agent_id}",
            "kind": "generated_music",
            "mime": mime,
        },
        "summary": f"Generated music. [attachment:{saved.id} {saved.filename}]",
    }
    if meta:
        payload["extra"] = meta
    return json.dumps(payload, ensure_ascii=False)


music_generate_def = Tool(
    name="music_generate",
    description=(
        "Generate a song using the configured MiniMax music preset. "
        "Provide `prompt` for style/mood and `lyrics` with structure tags like [Verse]/[Chorus]. "
        "Set `is_instrumental=true` for instrumental-only tracks. "
        "Set `lyrics_optimizer=true` to auto-write lyrics from prompt when lyrics are empty. "
        "For cover models (music-cover), pass `audio_url` or `attachment_ids` with reference audio."
    ),
    parameters={
        "prompt": {
            "type": "string",
            "required": False,
            "description": "Music style/mood/scenario (e.g. 'Pop, upbeat, summer vibe')",
        },
        "lyrics": {
            "type": "string",
            "required": False,
            "description": "Song lyrics; use \\n between lines; tags: [Verse], [Chorus], etc.",
        },
        "is_instrumental": {
            "type": "boolean",
            "required": False,
            "description": "Generate instrumental music without vocals (music-2.6 models)",
            "default": False,
        },
        "lyrics_optimizer": {
            "type": "boolean",
            "required": False,
            "description": "Auto-generate lyrics from prompt when lyrics empty (music-2.6 models)",
            "default": False,
        },
        "audio_url": {
            "type": "string",
            "required": False,
            "description": "Reference audio URL for music-cover models",
        },
        "attachment_ids": {
            "type": "array",
            "required": False,
            "description": "Session attachment id(s) as reference audio for cover generation",
        },
        "cover_feature_id": {
            "type": "string",
            "required": False,
            "description": "Cover preprocess feature id (music-cover two-step workflow)",
        },
    },
    returns="JSON with audio{attachment_id, url, filename} and summary",
    category="vision",
)
