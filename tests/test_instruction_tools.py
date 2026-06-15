"""Tests for instruction_read tool."""

from __future__ import annotations

from pathlib import Path

from seed.integrations.instruction_release import publish_release
from seed_tools.instruction import instruction_read_handler


def test_instruction_read_section(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEED_PROJECT_ROOT", str(tmp_path))
    publish_release("demo", "v1", "## Alpha\n\nLine A\n\n## Beta\n\nLine B", base=tmp_path)
    out = instruction_read_handler(bundle="demo@v1", section="alpha")
    assert "Line A" in out
