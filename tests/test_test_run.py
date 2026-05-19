"""test_run tool detection."""

from __future__ import annotations

from pathlib import Path

from seed_tools.test_run_tools import _detect_framework


def test_detect_pytest(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    assert _detect_framework(tmp_path) == "pytest"


def test_detect_npm(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    assert _detect_framework(tmp_path) == "npm"
