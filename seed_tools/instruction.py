"""Read locked instruction release sections (task runs)."""

from __future__ import annotations

from seed.core.agent_context import get_active_instruction_bundle
from seed.core.models import Tool
from seed.integrations.instruction_release import read_section_text


def instruction_read_handler(
    bundle: str = "",
    section: str = "",
    pattern: str = "",
    start_line: int = 0,
    end_line: int = 0,
    max_chars: int = 12000,
) -> str:
    ref = (bundle or "").strip() or get_active_instruction_bundle() or ""
    if not ref:
        return "Error: no instruction bundle (set bundle= or run within a task with instruction_bundle)"
    try:
        return read_section_text(
            ref,
            section=(section or "").strip() or None,
            pattern=(pattern or "").strip() or None,
            start_line=int(start_line) if start_line else None,
            end_line=int(end_line) if end_line else None,
            max_chars=int(max_chars or 12000),
        )
    except Exception as e:
        return f"Error: {e}"


instruction_read_def = Tool(
    name="instruction_read",
    description=(
        "Read a section or line range from the locked instruction release bundle "
        "(use section id from bootstrap TOC)."
    ),
    parameters={
        "bundle": {
            "type": "string",
            "required": False,
            "description": "Bundle ref name@version; defaults to current task bundle",
        },
        "section": {
            "type": "string",
            "required": False,
            "description": "Section id from manifest TOC",
        },
        "pattern": {
            "type": "string",
            "required": False,
            "description": "Substring search across full.md",
        },
        "start_line": {"type": "integer", "required": False},
        "end_line": {"type": "integer", "required": False},
        "max_chars": {"type": "integer", "required": False, "description": "Default 12000"},
    },
    returns="string: section text or matches",
    category="instruction",
)
