"""Cron apply tool (writes canonical seed.cron.json)."""
from __future__ import annotations

import json
import logging
from dataclasses import replace

from seed.core.models import Tool

logger = logging.getLogger(__name__)


def seed_cron_apply_handler(content: str) -> str:
    """Write full cron JSON to config/seed.cron.json and reload scheduler."""
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            return "Error: root JSON value must be an object"
    except json.JSONDecodeError as e:
        return f"Error: invalid JSON: {e}"
    try:
        from seed.integrations.cron_sched import (
            cron_config_canonical_path,
            reload_cron_scheduler,
        )

        path = cron_config_canonical_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        reload_result = reload_cron_scheduler()
        jobs = data.get("jobs")
        n = len(jobs) if isinstance(jobs, list) else 0
        return (
            f"seed_cron_apply: wrote {path} ({len(content)} chars); "
            f"reload={reload_result}; enabled={data.get('enabled')!r}; jobs={n}."
        )
    except Exception as e:
        logger.exception("seed_cron_apply")
        return f"seed_cron_apply error: {e}"


codeagent_cron_apply_handler = seed_cron_apply_handler

seed_cron_apply_def = Tool(
    name="seed_cron_apply",
    description=(
        "Replace entire config/seed.cron.json with the given UTF-8 JSON string and hot-reload the cron scheduler. "
        "Use seed_cron_path or file_read first if you need the current file. "
        "Schema: enabled (bool), jobs (array of {id, enabled, cron, timezone?, agent_id, session_id, prompt, max_tool_rounds?}); "
        "optional _readme and _example_job keys are ignored by the scheduler."
    ),
    parameters={
        "content": {
            "type": "string",
            "required": True,
            "description": "Complete JSON document for seed.cron.json",
        }
    },
    returns="string: result summary",
    category="seed",
)

codeagent_cron_apply_def = replace(
    seed_cron_apply_def,
    name="codeagent_cron_apply",
    description="Deprecated alias for seed_cron_apply.",
)


# ── Cron path / reload tools ──────────────────────────────────────────


def seed_cron_path_handler() -> str:
    try:
        from seed.integrations.cron_sched import cron_config_resolved_path

        return str(cron_config_resolved_path().resolve())
    except Exception as e:
        return f"Error: {e}"


codeagent_cron_path_handler = seed_cron_path_handler

seed_cron_path_def = Tool(
    name="seed_cron_path",
    description=(
        "Return absolute path to the active cron JSON (config/seed.cron.json, or legacy codeagent.cron.json). "
        "Use with file_read/file_write; after writing, call seed_cron_reload. "
        "Or use seed_cron_apply to write valid JSON and reload in one step."
    ),
    parameters={},
    returns="string: filesystem path",
    category="seed",
)

codeagent_cron_path_def = replace(
    seed_cron_path_def,
    name="codeagent_cron_path",
    description="Deprecated alias for seed_cron_path (same behavior).",
)


def seed_cron_reload_handler() -> str:
    try:
        from seed.integrations.cron_sched import (
            cron_status_for_ui,
            reload_cron_scheduler,
        )

        reload_result = reload_cron_scheduler()
        st = cron_status_for_ui()
        jobs = st.get("scheduled_jobs") or []
        lines = [
            f"seed_cron_reload: {reload_result}",
            f"scheduler_running={st.get('scheduler_running')}",
            f"config_enabled={st.get('config_enabled')}",
            f"env_disabled={st.get('env_disabled')}",
            f"registered_jobs={len(jobs)}",
        ]
        for j in jobs[:16]:
            lines.append(f"  - {j.get('id')} next={j.get('next_run')}")
        return "\n".join(lines)
    except Exception as e:
        logger.exception("seed_cron_reload")
        return f"seed_cron_reload error: {e}"


codeagent_cron_reload_handler = seed_cron_reload_handler

seed_cron_reload_def = Tool(
    name="seed_cron_reload",
    description=(
        "After editing config/seed.cron.json (or legacy codeagent.cron.json) with file_write, "
        "call this to apply changes without restarting the host process. "
        "Requires apscheduler and SEED_CRON not disabled."
    ),
    parameters={},
    returns="string: reload summary",
    category="seed",
)

codeagent_cron_reload_def = replace(
    seed_cron_reload_def,
    name="codeagent_cron_reload",
    description="Deprecated alias for seed_cron_reload.",
)
