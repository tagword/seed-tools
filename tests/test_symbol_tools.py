"""symbol_search tool."""

from __future__ import annotations

from seed_tools.symbol_tools import symbol_search_handler


def test_symbol_search_finds_name(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "x.py").write_text("def my_helper():\n    return 1\n", encoding="utf-8")
    out = symbol_search_handler("my_helper", path=str(tmp_path))
    assert "my_helper" in out
