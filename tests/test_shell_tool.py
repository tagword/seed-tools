"""bash uses exec_backend."""

from __future__ import annotations

from unittest.mock import patch

from seed_tools.bash import bash_handler


def test_bash_tool_uses_run_shell(monkeypatch) -> None:
    monkeypatch.setenv("SEED_EXEC_BACKEND", "local")

    with patch("seed.integrations.exec_backend.run_shell", return_value=(0, "ok-out")) as rs:
        out = bash_handler("echo x", timeout=5)
    rs.assert_called_once()
    assert "[exec:" in out
    assert "ok-out" in out
