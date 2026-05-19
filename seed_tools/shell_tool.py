"""Bash tool wrapper"""
import logging
from typing import Optional

from seed.core.models import Tool

logger = logging.getLogger(__name__)


def bash_tool_handler(command: str, timeout: int = 30, cwd: Optional[str] = None) -> str:
    """Execute a shell command with safety checks (local or Docker backend)."""
    from seed.core.agent_context import get_active_project_workspace_cwd
    from seed.integrations.exec_backend import exec_backend_label, run_shell
    from seed.integrations.safety import check_bash_command, enforce_bash_timeout

    if not (cwd or "").strip():
        cwd = get_active_project_workspace_cwd()
    err = check_bash_command(command, cwd=cwd)
    if err is not None:
        return err

    safe_timeout = enforce_bash_timeout(timeout)
    returncode, output = run_shell(command, timeout=safe_timeout, cwd=cwd)
    header = f"[exec: {exec_backend_label()}]\n"
    if returncode == 0:
        return header + output if output else header + "(no output)"
    if returncode == -1:
        return header + output
    return f"{header}Command failed with exit code {returncode}:\n{output}"

bash_def = Tool(
    name="bash_tool",
    description="Execute shell commands with safety checks",
    parameters={
        "command": {"type": "string", "required": True, "description": "Shell command to execute"},
        "timeout": {"type": "integer", "required": False, "description": "Timeout in seconds", "default": 30},
        "cwd": {"type": "string", "required": False, "description": "Working directory"}
    },
    returns="string: Command output or error message"
)

