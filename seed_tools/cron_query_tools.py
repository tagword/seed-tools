"""Cron path / reload tools (Seed canonical names + legacy alias tool names)."""
from __future__ import annotations

import logging
from dataclasses import replace

from seed.core.models import Tool

logger = logging.getLogger(__name__)


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
        from seed.integrations.cron_sched import cron_status_for_ui, reload_cron_scheduler

        reload_cron_scheduler()
        st = cron_status_for_ui()
        jobs = st.get("scheduled_jobs") or []
        lines = [
            "seed_cron_reload: ok",
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
