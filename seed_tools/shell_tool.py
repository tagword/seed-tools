"""Bash tool wrapper"""
import logging
import re
from typing import Optional

from seed.core.models import Tool

logger = logging.getLogger(__name__)

# Pattern for task management commands: task <action> [<task_id>] [--tail=N]
_TASK_CMD_RE = re.compile(
    r"^task\s+(status|log|stop|list)\s*(?:(\w+))?\s*(?:--tail=(\d+))?\s*$"
)


def bash_tool_handler(command: str, timeout: int = 30, cwd: Optional[str] = None, detach: bool = False) -> str:
    """Execute a shell command with safety checks (local or Docker backend)."""
    from seed.core.agent_context import get_active_project_workspace_cwd

    # ── Resolve cwd early (needed for both task commands and shell execution) ──
    if not (cwd or "").strip():
        cwd = get_active_project_workspace_cwd()

    # ── Intercept task management commands ──
    if not detach:
        m = _TASK_CMD_RE.match(command)
        if m:
            action = m.group(1)
            task_id = m.group(2)
            tail = int(m.group(3)) if m.group(3) else 20
            return _handle_task_command(action, task_id, tail, cwd)

    from seed.integrations.exec_backend import exec_backend_label, run_shell
    from seed.integrations.safety import check_bash_command, enforce_bash_timeout

    err = check_bash_command(command, cwd=cwd)
    if err is not None:
        return err

    safe_timeout = enforce_bash_timeout(timeout)
    returncode, output = run_shell(command, timeout=safe_timeout, cwd=cwd, detach=detach)
    header = f"[exec: {exec_backend_label()}]\n"
    if returncode == 0:
        return header + output if output else header + "(no output)"
    if returncode == -1:
        return header + output
    return f"{header}Command failed with exit code {returncode}:\n{output}"


def _handle_task_command(action: str, task_id: Optional[str], tail: int, cwd: Optional[str]) -> str:
    """Dispatch task management commands to the appropriate handler."""
    from seed.integrations.exec_backend import (
        detach_task_list,
        detach_task_log,
        detach_task_status,
        detach_task_stop,
    )

    try:
        if action == "list":
            return detach_task_list(cwd=cwd)
        if not task_id:
            return f"Usage: task {action} <task_id>"
        if action == "status":
            return detach_task_status(task_id, cwd=cwd)
        if action == "log":
            return detach_task_log(task_id, tail=tail, cwd=cwd)
        if action == "stop":
            return detach_task_stop(task_id, cwd=cwd)
    except Exception as e:
        return f"Error managing task: {e}"
    return f"Unknown task action: {action}"

bash_def = Tool(
    name="bash_tool",
    description="Execute shell commands with safety checks",
    parameters={
        "command": {"type": "string", "required": True, "description": "Shell command to execute"},
        "timeout": {"type": "integer", "required": False, "description": "Timeout in seconds", "default": 30},
        "cwd": {"type": "string", "required": False, "description": "Working directory"},
        "detach": {"type": "boolean", "required": False, "description": "Run in background without blocking", "default": False}
    },
    returns="string: Command output or error message"
)

