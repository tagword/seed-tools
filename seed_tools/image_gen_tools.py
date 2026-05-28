"""Image generation tool (OpenAI-compatible /images/generations)."""

from __future__ import annotations

import base64
import json
import logging
import os
import uuid
from typing import Any, List, Optional

import requests

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
        return max(1, min(int(os.environ.get("CODEAGENT_IMAGE_GEN_MAX_COUNT", "4") or 4), 8))
    except ValueError:
        return 4


def _default_size() -> str:
    return os.environ.get("CODEAGENT_IMAGE_GEN_DEFAULT_SIZE", "1024x1024").strip() or "1024x1024"


def _images_url(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if base.endswith("/images/generations"):
        return base
    return f"{base}/images/generations"


def _auth_headers(preset: dict[str, Any]) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    key = str(preset.get("api_key") or "").strip()
    scheme = str(preset.get("auth_scheme") or "Bearer").strip() or "Bearer"
    if key:
        headers["Authorization"] = f"{scheme} {key}"
    return headers


def _decode_image_item(item: dict[str, Any]) -> bytes:
    b64 = item.get("b64_json")
    if b64:
        return base64.standard_b64decode(str(b64))
    url = str(item.get("url") or "").strip()
    if url:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        return resp.content
    raise ValueError("image item missing b64_json and url")


def call_image_generations(
    preset: dict[str, Any],
    *,
    prompt: str,
    size: str,
    n: int,
    quality: str = "",
) -> List[bytes]:
    model = str(preset.get("model") or "").strip()
    if not model:
        raise ValueError("image_gen preset missing model")
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "size": size,
    }
    q = (quality or "").strip().lower()
    if q in ("standard", "hd"):
        payload["quality"] = q
    payload["response_format"] = "b64_json"

    url = _images_url(str(preset.get("base_url") or ""))
    headers = _auth_headers(preset)
    timeout = int(os.environ.get("CODEAGENT_IMAGE_GEN_TIMEOUT_SEC", "180") or 180)

    resp = requests.post(url, json=payload, headers=headers, timeout=max(30, timeout))
    if resp.status_code >= 400 and payload.get("response_format"):
        payload.pop("response_format", None)
        resp = requests.post(url, json=payload, headers=headers, timeout=max(30, timeout))
    if resp.status_code >= 400:
        detail = resp.text[:500]
        try:
            detail = resp.json().get("error", detail)
            if isinstance(detail, dict):
                detail = detail.get("message") or str(detail)
        except Exception:
            pass
        raise ValueError(f"image generation failed ({resp.status_code}): {detail}")

    data = resp.json()
    items = data.get("data")
    if not isinstance(items, list) or not items:
        raise ValueError("image generation returned no data")
    out: List[bytes] = []
    for item in items:
        if isinstance(item, dict):
            out.append(_decode_image_item(item))
    if not out:
        raise ValueError("failed to decode generated images")
    return out


async def image_generate(
    prompt: str = "",
    size: str = "",
    n: int = 1,
    quality: str = "standard",
    negative_prompt: str = "",
) -> str:
    """Generate image(s) via configured image_gen preset; saves as session attachments."""
    text = (prompt or "").strip()
    if not text:
        return json.dumps({"error": "prompt required"}, ensure_ascii=False)

    try:
        from codeagent.core.image_gen_models import resolve_image_gen_preset
        from seed.core.agent_context import get_active_image_gen_preset

        preset = resolve_image_gen_preset(get_active_image_gen_preset() or None)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    sz = (size or _default_size()).strip()
    if sz not in _ALLOWED_SIZES:
        sz = _default_size()
    try:
        count = max(1, min(int(n), _max_images()))
    except (TypeError, ValueError):
        count = 1

    full_prompt = text
    neg = (negative_prompt or "").strip()
    if neg:
        full_prompt = f"{text}\n\nAvoid: {neg}"

    try:
        raw_images = call_image_generations(
            preset,
            prompt=full_prompt,
            size=sz,
            n=count,
            quality=quality or "standard",
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

    payload = {
        "prompt": text,
        "model": preset.get("model"),
        "size": sz,
        "images": images_out,
        "summary": f"Generated {len(images_out)} image(s). "
        + "; ".join(f"[attachment:{i['attachment_id']} {i['filename']}]" for i in images_out),
    }
    return json.dumps(payload, ensure_ascii=False)


image_generate_def = Tool(
    name="image_generate",
    description=(
        "Generate image(s) from a text prompt using the configured image generation model "
        "(OpenAI-compatible /images/generations). Returns attachment_id(s) for display/download. "
        "Use when the user asks to draw, design, or create an image."
    ),
    parameters={
        "prompt": {"type": "string", "required": True, "description": "Image description / prompt"},
        "size": {
            "type": "string",
            "required": False,
            "description": "e.g. 1024x1024, 1024x1792, 1792x1024",
            "default": "1024x1024",
        },
        "n": {"type": "integer", "required": False, "description": "Number of images (max 4)", "default": 1},
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
    },
    returns="JSON with images[{attachment_id, url, filename}] and summary",
    category="vision",
)
