"""Image generation tool (provider-dispatched protocols)."""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Any, List, Optional

from seed.core.models import Tool
from seed_tools.shell_helpers import _active_agent_and_session

logger = logging.getLogger(__name__)

_ALLOWED_SIZES = frozenset(
    {
        "256x256",
        "512x512",
        "1024x1024",
        "1024x1792",
        "1792x1024",
        "1536x1024",
        "1024x1536",
    }
)


def _max_images() -> int:
    try:
        return max(1, min(int(os.environ.get("CODEAGENT_IMAGE_GEN_MAX_COUNT", "4") or 4), 15))
    except ValueError:
        return 4


def _default_size() -> str:
    return os.environ.get("CODEAGENT_IMAGE_GEN_DEFAULT_SIZE", "1024x1024").strip() or "1024x1024"


def _attachment_to_image_ref(path: Path) -> str:
    raw = path.read_bytes()
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    if not mime.startswith("image/"):
        raise ValueError(f"attachment is not an image: {path.name}")
    b64 = base64.standard_b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def collect_reference_images(
    *,
    reference_image_urls: Optional[List[str]] = None,
    attachment_ids: Optional[List[str]] = None,
) -> List[str]:
    """Resolve reference images to URLs or data URLs for provider APIs."""
    out: List[str] = []
    if reference_image_urls:
        for u in reference_image_urls:
            u = str(u).strip()
            if u:
                out.append(u)
    ids: List[str] = []
    if attachment_ids:
        ids.extend(str(x).strip() for x in attachment_ids if str(x).strip())
    if not ids:
        return out
    from codeagent.core.attachments import resolve_attachment_path

    agent_id, session_id = _active_agent_and_session()
    for aid in ids:
        p = resolve_attachment_path(agent_id, session_id, aid)
        if not p or not p.is_file():
            raise ValueError(f"reference attachment not found: {aid}")
        out.append(_attachment_to_image_ref(p))
    return out


async def image_generate(
    prompt: str = "",
    size: str = "",
    n: int = 1,
    quality: str = "standard",
    negative_prompt: str = "",
    reference_image_urls: Optional[List[str]] = None,
    attachment_ids: Optional[List[str]] = None,
) -> str:
    """Generate image(s) via configured image_gen preset; saves as session attachments."""
    text = (prompt or "").strip()
    if not text:
        return json.dumps({"error": "prompt required"}, ensure_ascii=False)

    try:
        from codeagent.core.image_gen_models import resolve_image_gen_preset
        from seed.core.agent_context import get_active_image_gen_preset
        from seed.core.model_providers import call_image_generations, normalize_image_size

        preset = resolve_image_gen_preset(get_active_image_gen_preset() or None)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    sz = normalize_image_size(size or "", _default_size(), preset=preset)
    try:
        count = max(1, min(int(n), _max_images()))
    except (TypeError, ValueError):
        count = 1

    full_prompt = text
    neg = (negative_prompt or "").strip()
    if neg:
        full_prompt = f"{text}\n\nAvoid: {neg}"

    try:
        refs = collect_reference_images(
            reference_image_urls=reference_image_urls,
            attachment_ids=attachment_ids,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    try:
        raw_images = call_image_generations(
            preset,
            prompt=full_prompt,
            size=sz,
            n=count,
            quality=quality or "standard",
            reference_images=refs or None,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    agent_id, session_id = _active_agent_and_session()
    from codeagent.core.attachments import save_attachment

    images_out: list[dict[str, Any]] = []
    for idx, raw in enumerate(raw_images):
        fname = f"generated-{uuid.uuid4().hex[:8]}-{idx + 1}.png"
        try:
            meta = save_attachment(
                agent_id=agent_id,
                session_id=session_id,
                raw_bytes=raw,
                filename=fname,
                mime="image/png",
            )
            images_out.append(
                {
                    "attachment_id": meta.id,
                    "filename": meta.filename,
                    "url": f"/api/attachments/{meta.id}?session_id={session_id}&agent_id={agent_id}",
                    "kind": "generated_image",
                }
            )
        except Exception as e:
            logger.warning("save generated image failed: %s", e)

    if not images_out:
        return json.dumps({"error": "failed to save generated images"}, ensure_ascii=False)

    from seed.core.model_providers import resolve_provider_for_preset

    payload = {
        "prompt": text,
        "model": preset.get("model"),
        "provider": resolve_provider_for_preset(preset),
        "size": sz,
        "reference_count": len(refs),
        "images": images_out,
        "summary": f"Generated {len(images_out)} image(s). "
        + "; ".join(f"[attachment:{i['attachment_id']} {i['filename']}]" for i in images_out),
    }
    return json.dumps(payload, ensure_ascii=False)


image_generate_def = Tool(
    name="image_generate",
    description=(
        "Generate image(s) from a text prompt using the configured image generation preset. "
        "Provider selects protocol (OpenAI / MiniMax / 火山方舟 Seedream). "
        "For image-to-image, pass reference_image_urls and/or attachment_ids. "
        "Returns attachment_id(s) for display/download."
    ),
    parameters={
        "prompt": {"type": "string", "required": True, "description": "Image description / prompt"},
        "size": {
            "type": "string",
            "required": False,
            "description": (
                "OpenAI: 1024x1024, 1024x1792. MiniMax: 1:1, 16:9, 9:16. "
                "Volcengine: 2K, 3K, 4K or WxH (WxH auto-mapped to 2K where needed)"
            ),
            "default": "1024x1024",
        },
        "n": {
            "type": "integer",
            "required": False,
            "description": "Number of images (OpenAI/MiniMax up to 9; Volcengine sequential up to 15)",
            "default": 1,
        },
        "quality": {
            "type": "string",
            "required": False,
            "description": "standard | hd (provider-dependent)",
            "default": "standard",
        },
        "negative_prompt": {
            "type": "string",
            "required": False,
            "description": "Optional things to avoid in the image",
        },
        "reference_image_urls": {
            "type": "array",
            "required": False,
            "description": "Reference image URL(s) for image-to-image (MiniMax / Volcengine)",
        },
        "attachment_ids": {
            "type": "array",
            "required": False,
            "description": "Session attachment id(s) as reference images (converted to data URL)",
        },
    },
    returns="JSON with images[{attachment_id, url, filename}] and summary",
    category="vision",
)


def call_image_generations(
    preset: dict[str, Any],
    *,
    prompt: str,
    size: str,
    n: int,
    quality: str = "",
    reference_images: Optional[List[str]] = None,
) -> List[bytes]:
    from seed.core.model_providers import call_image_generations as _dispatch

    return _dispatch(
        preset,
        prompt=prompt,
        size=size,
        n=n,
        quality=quality,
        reference_images=reference_images,
    )
