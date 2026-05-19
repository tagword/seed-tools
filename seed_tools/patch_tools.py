"""Apply unified-diff patches with optional dry-run."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from seed.core.models import Tool


@dataclass
class _Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[Tuple[str, str]]  # (prefix, content)


_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _parse_unified_patch(patch: str) -> dict[str, List[_Hunk]]:
    """Parse unified diff into {filepath: [hunks]}."""
    files: dict[str, List[_Hunk]] = {}
    current_file: Optional[str] = None
    current_hunks: List[_Hunk] = []
    current: Optional[_Hunk] = None

    for raw in patch.splitlines():
        line = raw.rstrip("\n")
        if line.startswith("+++ b/") or line.startswith("+++ "):
            if current:
                current_hunks.append(current)
                current = None
            if current_file and current_hunks:
                files[current_file] = current_hunks
            path = line[4:].strip()
            if path.startswith("b/"):
                path = path[2:]
            current_file = path
            current_hunks = []
            current = None
            continue
        if line.startswith("--- "):
            continue
        m = _HUNK_RE.match(line)
        if m:
            if current:
                current_hunks.append(current)
            old_start = int(m.group(1))
            old_count = int(m.group(2) or "1")
            new_start = int(m.group(3))
            new_count = int(m.group(4) or "1")
            current = _Hunk(old_start, old_count, new_start, new_count, [])
            continue
        if current is None:
            continue
        if not line:
            current.lines.append((" ", ""))
        elif line[0] in (" ", "+", "-"):
            current.lines.append((line[0], line[1:]))
        else:
            continue

    if current:
        current_hunks.append(current)
    if current_file and current_hunks:
        files[current_file] = current_hunks
    return files


def _apply_hunks(original: List[str], hunks: List[_Hunk]) -> List[str]:
    out = list(original)
    offset = 0
    for h in hunks:
        start = h.old_start - 1 + offset
        if start < 0:
            start = 0
        new_lines: List[str] = []
        idx = start
        for prefix, content in h.lines:
            if prefix == " ":
                if idx < len(out):
                    new_lines.append(out[idx])
                else:
                    new_lines.append(content)
                idx += 1
            elif prefix == "-":
                idx += 1
            elif prefix == "+":
                new_lines.append(content)
        end = idx
        out = out[:start] + new_lines + out[end:]
        offset += len(new_lines) - (end - start)
    return out


def apply_patch_handler(patch: str, dry_run: bool = True, base_path: str = ".") -> str:
    if not (patch or "").strip():
        return "Empty patch"
    try:
        file_hunks = _parse_unified_patch(patch)
    except Exception as e:
        return f"Failed to parse patch: {e}"
    if not file_hunks:
        return "No file hunks found in patch (expect unified diff with +++ b/path headers)"

    base = Path(base_path).expanduser().resolve()
    reports: List[str] = []
    for rel, hunks in file_hunks.items():
        target = (base / rel).resolve()
        if not str(target).startswith(str(base)):
            return f"Refusing path outside base: {rel}"
        if not target.is_file():
            reports.append(f"SKIP {rel}: file not found")
            continue
        original = target.read_text(encoding="utf-8", errors="replace").splitlines()
        try:
            updated = _apply_hunks(original, hunks)
        except Exception as e:
            reports.append(f"FAIL {rel}: {e}")
            continue
        new_text = "\n".join(updated) + ("\n" if updated else "")
        if dry_run:
            reports.append(f"DRY-RUN {rel}: {len(hunks)} hunk(s), {len(original)} -> {len(updated)} lines")
        else:
            target.write_text(new_text, encoding="utf-8")
            reports.append(f"APPLIED {rel}: {len(hunks)} hunk(s)")
    mode = "dry-run" if dry_run else "apply"
    return f"Patch {mode}:\n" + "\n".join(reports)


apply_patch_def = Tool(
    name="apply_patch",
    description="Apply a unified diff patch to files under base_path (dry_run=true by default)",
    parameters={
        "patch": {"type": "string", "required": True, "description": "Unified diff text"},
        "dry_run": {
            "type": "boolean",
            "required": False,
            "description": "If true, only report changes",
            "default": True,
        },
        "base_path": {
            "type": "string",
            "required": False,
            "description": "Root directory for relative paths in patch",
            "default": ".",
        },
    },
    returns="string",
    category="code",
)
