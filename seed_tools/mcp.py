"""MCP bridge tools — list servers/tools and call remote MCP tools."""

from __future__ import annotations

import json
from typing import Any

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
        transport = r.get("transport") or "stdio"
        if transport in ("sse", "streamable-http"):
            target = r.get("url") or ""
        else:
            cmd = r.get("command") or ""
            args = " ".join(r.get("args") or [])
            target = f"{cmd} {args}".strip()
        lines.append(f"- {r['id']}: {st} ({transport}) — {target}".strip())
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


def mcp_list_skills_handler(server_id: str) -> str:
    from seed.integrations.mcp_client import MCPError, get_mcp_manager, mcp_globally_enabled

    if not mcp_globally_enabled():
        return "MCP is disabled."
    sid = (server_id or "").strip()
    if not sid:
        return "server_id is required"
    try:
        skills = get_mcp_manager().get_session(sid).list_skills()
    except MCPError as e:
        return str(e)
    if not skills:
        return f"No skills from MCP server {sid!r}."
    lines = [f"Skills on MCP server {sid!r}:"]
    for s in skills:
        arg_names = [str(a.get("name") or "").strip() for a in s.arguments]
        suffix = f" ({', '.join(a for a in arg_names if a)})" if arg_names else ""
        lines.append(f"- {s.name}{suffix}: {s.description or '(no description)'}")
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
    try:
        timeout = float(pick_default("120", *MCP_CALL_TIMEOUT) or "120")
    except (TypeError, ValueError):
        timeout = 120.0
    timeout = max(1.0, min(timeout, 900.0))
    try:
        return get_mcp_manager().get_session(sid).call_tool(tname, args_obj, timeout=timeout)
    except MCPError as e:
        return str(e)


def mcp_skill_handler(
    server_id: str,
    skill_name: str,
    arguments: str = "{}",
) -> str:
    from seed.core.env_access import MCP_CALL_TIMEOUT, pick_default
    from seed.integrations.mcp_client import MCPError, get_mcp_manager, mcp_globally_enabled

    if not mcp_globally_enabled():
        return "MCP is disabled."
    sid = (server_id or "").strip()
    sname = (skill_name or "").strip()
    if not sid or not sname:
        return "server_id and skill_name are required"
    try:
        args_obj: Any = json.loads(arguments or "{}")
    except json.JSONDecodeError as e:
        return f"Invalid arguments JSON: {e}"
    if not isinstance(args_obj, dict):
        return "arguments must be a JSON object"
    try:
        timeout = float(pick_default("120", *MCP_CALL_TIMEOUT) or "120")
    except (TypeError, ValueError):
        timeout = 120.0
    timeout = max(1.0, min(timeout, 900.0))
    try:
        return get_mcp_manager().get_session(sid).call_skill(sname, args_obj, timeout=timeout)
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
    description="List tools exposed by an MCP server",
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

mcp_list_skills_def = Tool(
    name="mcp_list_skills",
    description="List skills/prompts exposed by an MCP server",
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

mcp_skill_def = Tool(
    name="mcp_skill",
    description="Invoke a skill/prompt on an MCP server",
    parameters={
        "server_id": {
            "type": "string",
            "required": True,
            "description": "MCP server id",
        },
        "skill_name": {
            "type": "string",
            "required": True,
            "description": "Skill or prompt name from mcp_list_skills",
        },
        "arguments": {
            "type": "string",
            "required": False,
            "description": "JSON object of skill arguments",
            "default": "{}",
        },
    },
    returns="string",
    category="mcp",
)
