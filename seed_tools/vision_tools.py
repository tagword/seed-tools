"""Vision analysis tools (tool-first multimodal)."""

from __future__ import annotations

import base64
import fnmatch
import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, List, Optional

from seed.core.models import Tool
from seed_tools.artifact_helpers import _artifact_summary, _artifact_write_text
from seed_tools.shell_helpers import _active_agent_and_session, _env_truthy

logger = logging.getLogger(__name__)


def _vision_analyze_max_images() -> int:
    try:
        return int(os.environ.get("CODEAGENT_VISION_ANALYZE_MAX_IMAGES", "4") or 4)
    except ValueError:
        return 4


def _read_image_data_url(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    if mime == "image/svg+xml":
        raise ValueError("SVG not supported for vision")
    b64 = base64.standard_b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}", mime


def _resolve_attachment_paths(ids: List[str]) -> List[tuple[str, Path]]:
    from seed.core.media_store import resolve_session_media_path

    agent_id, session_id = _active_agent_and_session()
    out: List[tuple[str, Path]] = []
    for aid in ids:
        aid = (aid or "").strip()
        if not aid:
            continue
        p = resolve_session_media_path(agent_id, session_id, aid)
        if not p or not p.is_file():
            raise ValueError(f"attachment not found: {aid}")
        out.append((aid, p))
    return out


def _build_vision_prompt(query: str, focus: str, detail: str, n_images: int) -> str:
    parts = ["Analyze the attached image(s) and respond in Chinese unless the user asked otherwise."]
    if query.strip():
        parts.append(f"User question: {query.strip()}")
    if focus.strip():
        parts.append(f"Focus on: {focus.strip()}")
    if detail == "brief":
        parts.append("Keep the answer concise.")
    elif detail == "ocr":
        parts.append("Extract visible text (OCR) accurately.")
    elif detail == "detailed":
        parts.append("Provide a detailed structured description.")
    if n_images > 1:
        parts.append(f"Compare all {n_images} images when relevant.")
    return "\n".join(parts)


def _call_vision_llm(paths: List[tuple[str, Path]], prompt: str) -> str:
    from seed.core.agent_context import get_active_vision_preset
    from seed.core.llm_presets import llm_executor_from_resolved
    from seed_tools._preset_helpers import resolve_capability_preset

    try:
        preset = resolve_capability_preset(
            "supports_vision",
            "CODEAGENT_VISION_PRESET_ID",
            get_active_vision_preset,
            "vision",
        )
        llm = llm_executor_from_resolved(preset)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    content: List[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for _aid, p in paths:
        try:
            url, _mime = _read_image_data_url(p)
        except Exception as ex:
            return json.dumps({"error": f"read {p.name}: {ex}"}, ensure_ascii=False)
        content.append({"type": "image_url", "image_url": {"url": url}})

    try:
        max_tokens = int(os.environ.get("CODEAGENT_VISION_MAX_TOKENS", "4096") or 4096)
    except ValueError:
        max_tokens = 4096

    text, meta = llm.generate(
        [{"role": "user", "content": content}],
        tools=None,
        max_tokens=max(256, min(max_tokens, 8192)),
    )
    result = (text or "").strip()
    if not result:
        result = "[vision_analyze: empty response]"
    usage = meta.get("usage") if isinstance(meta, dict) else None
    return result, usage


async def vision_analyze(
    attachment_id: str = "",
    attachment_ids: Optional[List[str]] = None,
    query: str = "",
    focus: str = "",
    detail: str = "auto",
) -> str:
    """Analyze image attachment(s) with the configured vision model; returns JSON text."""
    ids: List[str] = []
    if attachment_ids:
        ids.extend(str(x).strip() for x in attachment_ids if str(x).strip())
    if attachment_id.strip():
        ids.insert(0, attachment_id.strip())
    ids = list(dict.fromkeys(ids))
    if not ids:
        return json.dumps({"error": "attachment_id or attachment_ids required"}, ensure_ascii=False)

    max_n = _vision_analyze_max_images()
    if len(ids) > max_n:
        return json.dumps(
            {"error": f"at most {max_n} images per call; got {len(ids)}"},
            ensure_ascii=False,
        )

    det = (detail or "auto").strip().lower()
    if det not in ("auto", "brief", "detailed", "ocr"):
        det = "auto"

    try:
        paths = _resolve_attachment_paths(ids)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    prompt = _build_vision_prompt(query, focus, det, len(paths))
    try:
        result_text, usage = _call_vision_llm(paths, prompt)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    analyses = []
    if len(paths) == 1:
        analyses.append({"attachment_id": paths[0][0], "summary": result_text[:2000]})
    else:
        for aid, _p in paths:
            analyses.append({"attachment_id": aid, "summary": "(multi-image batch)"})

    payload: dict[str, Any] = {
        "summary": result_text,
        "attachment_ids": [a for a, _ in paths],
        "analyses": analyses,
    }
    if usage:
        payload["usage"] = usage
        _accumulate_vision_usage(usage)

    try:
        max_inline = int(os.environ.get("CODEAGENT_VISION_RESULT_MAX_CHARS", "12000") or 12000)
    except ValueError:
        max_inline = 12000

    if len(result_text) > max_inline and _env_truthy("SEED_TOOL_ARTIFACTS", "1"):
        ap = _artifact_write_text(
            kind="vision_analyze",
            name_hint="vision",
            text=result_text,
        )
        if ap:
            payload["artifact_path"] = ap
            payload["summary"] = _artifact_summary(
                title="[vision_analyze]",
                text=result_text,
                path=ap,
            )

    _update_vision_context(paths, payload)
    return json.dumps(payload, ensure_ascii=False)


def _accumulate_vision_usage(usage: dict[str, Any]) -> None:
    """Accumulate raw token usage in session metadata (no cost calc — that's codeagent's domain)."""
    try:
        from seed.core.llm_sess import load_or_create_chat_session, persist_chat_session
        from seed.core.usage_accumulator import record_round_usage
        from seed_tools._preset_helpers import resolve_capability_preset

        agent_id, session_id = _active_agent_and_session()
        record_round_usage({"usage": usage})

        from seed.core.agent_context import get_active_vision_preset

        try:
            preset = resolve_capability_preset(
                "supports_vision",
                "CODEAGENT_VISION_PRESET_ID",
                get_active_vision_preset,
                "vision",
            )
            model_name = str(preset.get("model") or "vision")
        except Exception:
            model_name = "vision"

        _USAGE_KEYS = (
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "prompt_cache_hit_tokens",
            "prompt_cache_miss_tokens",
        )

        sess = load_or_create_chat_session(session_id, agent_id)
        if not isinstance(sess.metadata, dict):
            sess.metadata = {}
        prev = sess.metadata.get("accumulated_usage", {}) or {}
        acc: dict[str, Any] = {}
        for k in _USAGE_KEYS:
            v = usage.get(k, 0)
            if isinstance(v, (int, float)):
                acc[k] = int(prev.get(k, 0) or 0) + int(v)
        per_model = dict(prev.get("per_model") or {})
        model_acc = dict(per_model.get(model_name) or {})
        for k in _USAGE_KEYS:
            v = usage.get(k, 0)
            if isinstance(v, (int, float)):
                model_acc[k] = int(model_acc.get(k, 0) or 0) + int(v)
        model_acc["source"] = "vision_analyze"
        per_model[model_name] = model_acc
        acc["per_model"] = per_model
        sess.metadata["accumulated_usage"] = acc
        persist_chat_session(sess, agent_id)
    except Exception:
        logger.debug("vision usage accumulate skipped", exc_info=True)


def _update_vision_context(paths: List[tuple[str, Path]], payload: dict[str, Any]) -> None:
    try:
        from seed.core.llm_sess import load_or_create_chat_session, persist_chat_session

        agent_id, session_id = _active_agent_and_session()
        sess = load_or_create_chat_session(session_id, agent_id)
        if not isinstance(sess.metadata, dict):
            sess.metadata = {}
        vc = sess.metadata.get("vision_context")
        if not isinstance(vc, dict):
            vc = {"attachments": {}}
        att_map = vc.get("attachments")
        if not isinstance(att_map, dict):
            att_map = {}
        preview = str(payload.get("summary") or "")[:500]
        for aid, _ in paths:
            att_map[aid] = {"summary_preview": preview, "analyzed": True}
        vc["attachments"] = att_map
        sess.metadata["vision_context"] = vc
        persist_chat_session(sess, agent_id)
    except Exception:
        logger.debug("vision_context update skipped", exc_info=True)


async def vision_analyze_directory(
    directory: str,
    query: str = "",
    pattern: str = "",
    max_files: int = 20,
    batch_size: int = 4,
) -> str:
    """Scan a workspace directory for images and analyze in batches."""
    from seed.core.agent_context import get_active_project_workspace_cwd
    from seed.core.media_store import save_session_media

    workspace = get_active_project_workspace_cwd()
    if not workspace:
        return json.dumps({"error": "no active project workspace for directory scan"}, ensure_ascii=False)

    try:
        paths, truncated = _scan_image_directory(
            Path(workspace),
            directory,
            pattern=pattern or None,
            max_files=max(1, min(int(max_files), 32)),
        )
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    if not paths:
        return json.dumps({"error": f"no images in {directory}"}, ensure_ascii=False)

    agent_id, session_id = _active_agent_and_session()
    attachment_ids: List[str] = []
    for p in paths:
        try:
            aid, _ = save_session_media(
                agent_id=agent_id,
                session_id=session_id,
                raw_bytes=p.read_bytes(),
                filename=p.name,
                mime=mimetypes.guess_type(str(p))[0] or "image/png",
            )
            attachment_ids.append(aid)
        except Exception as e:
            logger.warning("skip %s: %s", p, e)

    if not attachment_ids:
        return json.dumps({"error": "failed to stage directory images"}, ensure_ascii=False)

    bs = max(1, min(int(batch_size), _vision_analyze_max_images()))
    summaries: List[dict[str, Any]] = []
    for i in range(0, len(attachment_ids), bs):
        batch = attachment_ids[i : i + bs]
        raw = await vision_analyze(
            attachment_ids=batch,
            query=query or f"Summarize images in {directory}",
        )
        try:
            j = json.loads(raw)
            summaries.append({"batch": batch, "result": j})
        except json.JSONDecodeError:
            summaries.append({"batch": batch, "result": {"summary": raw}})

    out = {
        "directory": directory,
        "total": len(attachment_ids),
        "truncated": truncated,
        "attachment_ids": attachment_ids,
        "batches": summaries,
    }
    combined = json.dumps(out, ensure_ascii=False)
    if len(combined) > 15000 and _env_truthy("SEED_TOOL_ARTIFACTS", "1"):
        ap = _artifact_write_text(kind="vision_analyze_directory", name_hint="dir", text=combined)
        if ap:
            out["artifact_path"] = ap
            out["summary"] = f"Analyzed {len(attachment_ids)} images; full report at {ap}"
            return json.dumps(out, ensure_ascii=False)
    return combined


_DEFAULT_IMAGE_GLOBS = ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif", "*.bmp")


def _scan_image_directory(
    workspace_root: Path,
    rel_path: str,
    *,
    pattern: str | None = None,
    max_files: int | None = None,
) -> tuple[list[Path], bool]:
    """Scan a directory for image files. Returns (paths, truncated)."""
    root = workspace_root.resolve()
    rel = (rel_path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in rel.split("/"):
        raise ValueError("path traversal not allowed")
    target = (root / rel).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("path outside workspace")
    if not target.is_dir():
        raise ValueError(f"not a directory: {rel_path}")

    globs = _parse_image_globs(pattern)
    limit = max_files or 32
    found: list[Path] = []
    truncated = False
    for dirpath, _, filenames in os.walk(target):
        for name in sorted(filenames):
            if not _matches_image_glob(name, globs):
                continue
            p = Path(dirpath) / name
            if not p.is_file():
                continue
            found.append(p.resolve())
            if len(found) >= limit:
                truncated = True
                return found, truncated
    return found, truncated


def _parse_image_globs(pattern: str | None) -> tuple[str, ...]:
    if pattern and pattern.strip():
        return tuple(g.strip() for g in pattern.split(",") if g.strip())
    return _DEFAULT_IMAGE_GLOBS


def _matches_image_glob(name: str, globs: tuple[str, ...]) -> bool:
    low = name.lower()
    for g in globs:
        if fnmatch.fnmatch(low, g.lower()):
            return True
    return False


vision_analyze_def = Tool(
    name="vision_analyze",
    description=(
        "Analyze image attachment(s) using the vision model. "
        "Call when user message contains [attachment:...]. "
        "Returns text summary (never raw image to main context)."
    ),
    parameters={
        "attachment_id": {
            "type": "string",
            "required": False,
            "description": "Single attachment id",
        },
        "attachment_ids": {
            "type": "array",
            "required": False,
            "description": "Multiple attachment ids (max 4 per call)",
        },
        "query": {"type": "string", "required": False, "description": "User question about the image(s)"},
        "focus": {"type": "string", "required": False, "description": "Region or aspect to focus on"},
        "detail": {
            "type": "string",
            "required": False,
            "description": "brief | detailed | ocr | auto",
            "default": "auto",
        },
    },
    returns="JSON with summary and optional artifact_path",
    category="vision",
)

vision_analyze_directory_def = Tool(
    name="vision_analyze_directory",
    description=(
        "Scan a directory under the active project workspace for images and analyze them in batches. "
        "Use when user references [image_dir:...] or a folder path."
    ),
    parameters={
        "directory": {"type": "string", "required": True, "description": "Relative directory under workspace"},
        "query": {"type": "string", "required": False, "description": "Analysis goal"},
        "pattern": {
            "type": "string",
            "required": False,
            "description": "Glob patterns comma-separated, e.g. *.png,*.jpg",
        },
        "max_files": {"type": "integer", "required": False, "default": 20},
        "batch_size": {"type": "integer", "required": False, "default": 4},
    },
    returns="JSON summary of directory analysis",
    category="vision",
)
