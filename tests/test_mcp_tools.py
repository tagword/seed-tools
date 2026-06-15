"""MCP tool handlers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from seed_tools.mcp import mcp_servers_handler


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
