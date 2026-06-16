"""MCP tool handlers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from seed_tools.mcp import mcp_call_handler, mcp_servers_handler


def test_mcp_servers_disabled(monkeypatch) -> None:
    monkeypatch.setenv("SEED_MCP_ENABLED", "0")
    assert "disabled" in mcp_servers_handler().lower()


def test_mcp_servers_lists(monkeypatch) -> None:
    monkeypatch.setenv("SEED_MCP_ENABLED", "1")
    with patch(
        "seed.integrations.mcp_client.get_mcp_manager",
    ) as gm:
        gm.return_value.list_servers_status.return_value = [
            {"id": "fs", "enabled": True, "connected": False, "command": "npx", "args": []}
        ]
        out = mcp_servers_handler()
    assert "fs" in out


def test_mcp_call_clamps_timeout(monkeypatch) -> None:
    monkeypatch.setenv("SEED_MCP_ENABLED", "1")
    import seed.core.env_access as _ea

    monkeypatch.setattr(_ea, "MCP_CALL_TIMEOUT", ("SEED_MCP_CALL_TIMEOUT",))
    monkeypatch.setattr(_ea, "pick_default", lambda default, *keys: "99999")

    mock_sess = MagicMock()
    mock_sess.call_tool.return_value = "ok"
    with patch("seed.integrations.mcp_client.mcp_globally_enabled", return_value=True), patch(
        "seed.integrations.mcp_client.get_mcp_manager"
    ) as gm:
        gm.return_value.get_session.return_value = mock_sess
        out = mcp_call_handler("fs", "tool", "{}")
    assert out == "ok"
    assert mock_sess.call_tool.call_args.kwargs["timeout"] == 900.0
