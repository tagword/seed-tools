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
        from seed.integrations.cron_sched import cron_config_canonical_path, reload_cron_scheduler

        path = cron_config_canonical_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        reload_cron_scheduler()
        jobs = data.get("jobs")
        n = len(jobs) if isinstance(jobs, list) else 0
        return (
            f"seed_cron_apply: wrote {path} ({len(content)} chars); scheduler reloaded. "
            f"enabled={data.get('enabled')!r}; jobs={n}."
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
