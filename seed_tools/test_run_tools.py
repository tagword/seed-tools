"""Run project test suites (pytest / npm test) via the configured execution backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from seed.core.models import Tool


def _detect_framework(cwd: Path) -> str:
    if (cwd / "pytest.ini").is_file() or (cwd / "conftest.py").is_file():
        return "pytest"
    if (cwd / "pyproject.toml").is_file():
        try:
            text = (cwd / "pyproject.toml").read_text(encoding="utf-8")
            if "pytest" in text:
                return "pytest"
        except OSError:
            pass
    if (cwd / "package.json").is_file():
        return "npm"
    if list(cwd.glob("test_*.py")) or (cwd / "tests").is_dir():
        return "pytest"
    return ""


def test_run_handler(
    framework: str = "auto",
    extra_args: str = "",
    cwd: Optional[str] = None,
    timeout: int = 300,
) -> str:
    from seed.integrations.exec_backend import exec_backend_label, run_shell
    from seed.integrations.safety import check_bash_command, enforce_bash_timeout

    work = Path(cwd).expanduser().resolve() if cwd and str(cwd).strip() else Path.cwd().resolve()
    fw = (framework or "auto").strip().lower()
    if fw == "auto":
        fw = _detect_framework(work)
    if fw not in ("pytest", "npm"):
        return (
            f"Could not detect test framework under {work}. "
            "Set framework to 'pytest' or 'npm', or add pytest.ini / package.json."
        )

    if fw == "pytest":
        args = (extra_args or "").strip()
        command = f"python -m pytest {args}".strip() if args else "python -m pytest -q"
    else:
        command = "npm test"
        if extra_args.strip():
            command = f"npm test -- {extra_args.strip()}"

    err = check_bash_command(command, cwd=str(work))
    if err is not None:
        return err

    safe_timeout = enforce_bash_timeout(timeout)
    code, output = run_shell(command, timeout=safe_timeout, cwd=str(work))
    header = f"[test_run:{fw}] [exec: {exec_backend_label()}] cwd={work}\n"
    if code == 0:
        return header + (output or "(tests passed, no output)")
    return f"{header}Tests failed (exit {code}):\n{output}"


test_run_def = Tool(
    name="test_run",
    description=(
        "Run automated tests for the current project (pytest or npm test). "
        "Detects framework when framework=auto."
    ),
    parameters={
        "framework": {
            "type": "string",
            "required": False,
            "description": "auto | pytest | npm",
            "default": "auto",
        },
        "extra_args": {
            "type": "string",
            "required": False,
            "description": "Extra CLI args (e.g. tests/ -k foo)",
        },
        "cwd": {
            "type": "string",
            "required": False,
            "description": "Project directory (default: process cwd)",
        },
        "timeout": {
            "type": "integer",
            "required": False,
            "description": "Timeout seconds (default 300)",
            "default": 300,
        },
    },
    returns="string",
    category="code",
)
