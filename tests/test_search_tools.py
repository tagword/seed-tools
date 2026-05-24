"""Tests for grep/glob/file_search directory exclusions."""
from __future__ import annotations

import os
from pathlib import Path

from seed_tools.file_write_tools import (
    file_search_handler,
    glob_tool_handler,
    grep_tool_handler,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_grep_skips_dist_and_caps_line_length(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "src" / "app.py", "TARGET_HERE\n")
    _write(tmp_path / "web" / "dist" / "assets" / "index.js", "TARGET_HERE\n" + ("x" * 5000))

    results = grep_tool_handler("TARGET_HERE", directory=str(tmp_path))
    assert len(results) == 1
    assert "src/app.py" in results[0].replace("\\", "/")
    assert "dist" not in results[0]


def test_grep_caps_long_line(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    long_line = "MATCH_" + ("z" * 800)
    _write(tmp_path / "main.py", long_line + "\n")

    results = grep_tool_handler("MATCH_", directory=str(tmp_path))
    assert len(results) == 1
    assert "[line truncated" in results[0]
    assert len(results[0]) < 700


def test_glob_skips_node_modules(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "lib" / "util.py", "# ok\n")
    _write(tmp_path / "node_modules" / "pkg" / "index.js", "// skip\n")

    matches = glob_tool_handler("*.py", directory=str(tmp_path))
    normalized = [m.replace("\\", "/") for m in matches]
    assert any("/lib/util.py" in m for m in normalized)
    assert not any("node_modules" in m for m in normalized)


def test_file_search_skips_build_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "src" / "a.ts", "export {}\n")
    _write(tmp_path / "build" / "a.ts", "export {}\n")

    matches = file_search_handler("**/*.ts", directory=str(tmp_path))
    normalized = [m.replace("\\", "/") for m in matches]
    assert any("/src/a.ts" in m for m in normalized)
    assert not any("/build/" in m for m in normalized)
