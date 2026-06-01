"""Video generation tool (Agnes agnes-video-v2.0 API)."""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, List, Optional

from seed.core.models import Tool
from seed_tools.shell_helpers import _active_agent_and_session

logger = logging.getLogger(__name__)


def _public_attachment_url(agent_id: str, session_id: str, attachment_id: str) -> str:
    base = os.environ.get("CODEAGENT_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not base:
        raise ValueError(
            "attachment_ids for image-to-video require CODEAGENT_PUBLIC_BASE_URL "
            "(Agnes API must fetch public image URLs); or pass image_url / image_urls"
        )
    return (
        f"{base}/api/attachments/{attachment_id}"
        f"?session_id={session_id}&agent_id={agent_id}"
    )


def collect_reference_image_urls(
    *,
    image_url: str = "",
    image_urls: Optional[List[str]] = None,
    attachment_ids: Optional[List[str]] = None,
) -> tuple[str, list[str]]:
    """Return (single_image_url, multi_image_urls)."""
    urls = [str(u).strip() for u in (image_urls or []) if str(u).strip()]
    single = (image_url or "").strip()
    ids: List[str] = []
    if attachment_ids:
        ids.extend(str(x).strip() for x in attachment_ids if str(x).strip())
    if ids:
        agent_id, session_id = _active_agent_and_session()
        for aid in ids:
            urls.append(_public_attachment_url(agent_id, session_id, aid))
    if single and single not in urls:
        if urls:
            urls.insert(0, single)
        else:
            return single, []
    if len(urls) == 1:
        return urls[0], []
    return "", urls


async def video_generate(
    prompt: str = "",
    image_url: str = "",
    image_urls: Optional[List[str]] = None,
    attachment_ids: Optional[List[str]] = None,
    mode: str = "",
    height: int = 768,
    width: int = 1152,
    num_frames: int = 121,
    frame_rate: float = 24,
    num_inference_steps: Optional[int] = None,
    seed: Optional[int] = None,
    negative_prompt: str = "",
) -> str:
    """Generate a video via configured video preset; saves MP4 as session attachment."""
    text = (prompt or "").strip()
    if not text:
        return json.dumps({"error": "prompt required"}, ensure_ascii=False)

    try:
        from codeagent.core.video_models import resolve_video_gen_preset
        from seed.core.agent_context import get_active_video_gen_preset
        from seed.core.model_providers import call_video_generations, resolve_provider_for_preset

        preset = resolve_video_gen_preset(get_active_video_gen_preset() or None)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    try:
        single_url, multi_urls = collect_reference_image_urls(
            image_url=image_url,
            image_urls=image_urls,
            attachment_ids=attachment_ids,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    gen_mode = (mode or "").strip()
    if multi_urls and not gen_mode:
        gen_mode = "keyframes" if len(multi_urls) >= 2 else ""

    try:
        video_bytes, mime, meta = call_video_generations(
            preset,
            prompt=text,
            image_url=single_url,
            image_urls=multi_urls or None,
            mode=gen_mode,
            height=int(height),
            width=int(width),
            num_frames=int(num_frames),
            frame_rate=float(frame_rate),
            num_inference_steps=num_inference_steps,
            seed=seed,
            negative_prompt=negative_prompt,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    agent_id, session_id = _active_agent_and_session()
    from codeagent.core.attachments import save_attachment

    fname = f"generated-video-{uuid.uuid4().hex[:8]}.mp4"
    try:
        saved = save_attachment(
            agent_id=agent_id,
            session_id=session_id,
            raw_bytes=video_bytes,
            filename=fname,
            mime=mime or "video/mp4",
        )
    except Exception as e:
        logger.warning("save generated video failed: %s", e)
        return json.dumps({"error": "failed to save generated video"}, ensure_ascii=False)

    payload: dict[str, Any] = {
        "prompt": text,
        "model": preset.get("model"),
        "provider": resolve_provider_for_preset(preset),
        "height": int(height),
        "width": int(width),
        "num_frames": int(num_frames),
        "frame_rate": float(frame_rate),
        "mode": gen_mode or None,
        "video": {
            "attachment_id": saved.id,
            "filename": saved.filename,
            "url": f"/api/attachments/{saved.id}?session_id={session_id}&agent_id={agent_id}",
            "kind": "generated_video",
            "mime": mime or "video/mp4",
        },
        "summary": f"Generated video. [attachment:{saved.id} {saved.filename}]",
    }
    if meta:
        payload["extra"] = meta
    return json.dumps(payload, ensure_ascii=False)


video_generate_def = Tool(
    name="video_generate",
    description=(
        "Generate a video using the configured Agnes video preset (agnes-video-v2.0). "
        "Provide a cinematic `prompt` describing subject, action, scene, camera, and lighting. "
        "For image-to-video, pass `image_url` or `attachment_ids` (requires CODEAGENT_PUBLIC_BASE_URL). "
        "For multi-image or keyframe transitions, pass `image_urls` (2+ URLs) and optionally `mode=keyframes`."
    ),
    parameters={
        "prompt": {
            "type": "string",
            "required": True,
            "description": "Video description (subject + action + scene + camera + lighting + style)",
        },
        "image_url": {
            "type": "string",
            "required": False,
            "description": "Single reference image URL for image-to-video",
        },
        "image_urls": {
            "type": "array",
            "required": False,
            "description": "Multiple reference image URLs for multi-image or keyframe mode",
        },
        "attachment_ids": {
            "type": "array",
            "required": False,
            "description": "Session image attachment ids (need CODEAGENT_PUBLIC_BASE_URL for provider fetch)",
        },
        "mode": {
            "type": "string",
            "required": False,
            "description": "Generation mode, e.g. keyframes for keyframe interpolation",
        },
        "height": {
            "type": "integer",
            "required": False,
            "description": "Video height (default 768)",
            "default": 768,
        },
        "width": {
            "type": "integer",
            "required": False,
            "description": "Video width (default 1152)",
            "default": 1152,
        },
        "num_frames": {
            "type": "integer",
            "required": False,
            "description": "Frame count <=441, must satisfy 8n+1 (default 121)",
            "default": 121,
        },
        "frame_rate": {
            "type": "number",
            "required": False,
            "description": "FPS 1–60 (default 24)",
            "default": 24,
        },
        "num_inference_steps": {
            "type": "integer",
            "required": False,
            "description": "Optional inference steps",
        },
        "seed": {
            "type": "integer",
            "required": False,
            "description": "Random seed for reproducible output",
        },
        "negative_prompt": {
            "type": "string",
            "required": False,
            "description": "Content to avoid in the video",
        },
    },
    returns="JSON with video{attachment_id, url, filename} and summary",
    category="vision",
)
