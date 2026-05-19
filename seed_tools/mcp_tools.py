"""MCP bridge tools — list servers/tools and call remote MCP tools."""

from __future__ import annotations

import json
from typing import Any, Optional

from seed.core.models import Tool


def mcp_servers_handler() -> str:
    from seed.integrations.mcp_client import get_mcp_manager, mcp_globally_enabled

    if not mcp_globally_enabled():
        return "MCP is disabled (SEED_MCP_ENABLED=0)."
    rows = get_mcp_manager().list_servers_status()
    if not rows:
        return "No MCP servers configured. Edit config/mcp.json or use Web UI /api/mcp."
    lines = ["Configured MCP servers:"]
    for r in rows:
        st = "connected" if r.get("connected") else ("enabled" if r.get("enabled") else "disabled")
        cmd = r.get("command") or ""
        args = " ".join(r.get("args") or [])
        lines.append(f"- {r['id']}: {st} — {cmd} {args}".strip())
    return "\n".join(lines)


def mcp_list_tools_handler(server_id: str) -> str:
    from seed.integrations.mcp_client import MCPError, get_mcp_manager, mcp_globally_enabled

    if not mcp_globally_enabled():
        return "MCP is disabled."
    sid = (server_id or "").strip()
    if not sid:
        return "server_id is required"
    try:
        tools = get_mcp_manager().get_session(sid).list_tools()
    except MCPError as e:
        return str(e)
    if not tools:
        return f"No tools from MCP server {sid!r}."
    lines = [f"Tools on MCP server {sid!r}:"]
    for t in tools:
        lines.append(f"- {t.name}: {t.description or '(no description)'}")
    return "\n".join(lines)


def mcp_call_handler(
    server_id: str,
    tool_name: str,
    arguments: str = "{}",
) -> str:
    from seed.core.env_access import MCP_CALL_TIMEOUT, pick_default
    from seed.integrations.mcp_client import MCPError, get_mcp_manager, mcp_globally_enabled

    if not mcp_globally_enabled():
        return "MCP is disabled."
    sid = (server_id or "").strip()
    tname = (tool_name or "").strip()
    if not sid or not tname:
        return "server_id and tool_name are required"
    try:
        args_obj: Any = json.loads(arguments or "{}")
    except json.JSONDecodeError as e:
        return f"Invalid arguments JSON: {e}"
    if not isinstance(args_obj, dict):
        return "arguments must be a JSON object"
    timeout = float(pick_default("120", *MCP_CALL_TIMEOUT) or "120")
    try:
        return get_mcp_manager().get_session(sid).call_tool(tname, args_obj, timeout=timeout)
    except MCPError as e:
        return str(e)


mcp_servers_def = Tool(
    name="mcp_servers",
    description="List configured MCP servers and connection status",
    parameters={},
    returns="string",
    category="mcp",
)

mcp_list_tools_def = Tool(
    name="mcp_list_tools",
    description="List tools exposed by an MCP server (stdio)",
    parameters={
        "server_id": {
            "type": "string",
            "required": True,
            "description": "MCP server id from config/mcp.json",
        },
    },
    returns="string",
    category="mcp",
)

mcp_call_def = Tool(
    name="mcp_call",
    description="Invoke a tool on an MCP server",
    parameters={
        "server_id": {
            "type": "string",
            "required": True,
            "description": "MCP server id",
        },
        "tool_name": {
            "type": "string",
            "required": True,
            "description": "Tool name from mcp_list_tools",
        },
        "arguments": {
            "type": "string",
            "required": False,
            "description": "JSON object of tool arguments",
            "default": "{}",
        },
    },
    returns="string",
    category="mcp",
)
