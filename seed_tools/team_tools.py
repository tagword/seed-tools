"""Team tools — call_agent, dispatch, parallel.

负责人 Agent 通过这些工具调度团队成员。子 Agent 之间无直接交互，
所有通信通过负责人路由（API 网关模式）。

同进程模式：call_agent = 函数调用（零网络延迟）
跨进程模式：Phase 1 仅保留接口（由宿主提供 HTTP 端点）
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List

from seed.core.models import Tool
from seed.core.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


# ── Helper ──

async def _call_single(agent_id: str, task: str) -> Dict[str, Any]:
    """Call a single agent and return a result dict.

    Returns::
        {"agent_id": str, "task": str, "result": str}  or
        {"agent_id": str, "task": str, "error": str}
    """
    handle = AgentRegistry.get(agent_id)
    if not handle:
        return {
            "agent_id": agent_id,
            "task": task,
            "error": f"Agent '{agent_id}' not found in registry",
        }
    try:
        result = handle.run_task(task)
        return {"agent_id": agent_id, "task": task, "result": result}
    except Exception as e:
        logger.exception(f"call_agent '{agent_id}' failed: {e}")
        return {"agent_id": agent_id, "task": task, "error": str(e)}


# ── call_agent ──

async def call_agent(agent_id: str, task: str) -> str:
    """Call another agent with a task and wait for its result synchronously.

    Use when you need a specialist agent to complete a sub-task.

    Args:
        agent_id: Target agent identifier (as registered in AgentRegistry).
        task: Description of what to do.

    Returns:
        The agent's response text, or an error message.
    """
    result = await _call_single(agent_id, task)
    if "error" in result:
        return f"Error calling agent '{agent_id}': {result['error']}"
    return result.get("result", "No response")


call_agent_tool_def = Tool(
    name="call_agent",
    description=(
        "Call another agent with a task and wait for its result synchronously. "
        "Use when you need a specialist agent to complete a sub-task. "
        "Returns the agent's response text."
    ),
    parameters={
        "agent_id": {
            "type": "string",
            "required": True,
            "description": "Target agent id (registered in AgentRegistry)",
        },
        "task": {
            "type": "string",
            "required": True,
            "description": "Task description for the target agent",
        },
    },
    returns="string: agent's response text, or error message if not found/failed",
    category="team",
)


# ── dispatch ──

async def dispatch(
    tasks: List[Dict[str, str]],
    mode: str = "sequential",
) -> str:
    """Dispatch multiple tasks to agents in sequential or parallel mode.

    Use when you have multiple independent (parallel) or dependent (sequential)
    sub-tasks that different agents should handle.

    Args:
        tasks: List of {"agent_id": str, "task": str} objects.
        mode: "sequential" (default, one by one, stop on first error)
              or "parallel" (concurrent via asyncio.gather).

    Returns:
        JSON-encoded list of results, each element is:
          {"agent_id": str, "task": str, "result": str}
        or with "error" key on failure.
    """
    if not tasks:
        return json.dumps([], ensure_ascii=False)

    if mode == "sequential":
        results: List[Dict[str, Any]] = []
        for t in tasks:
            r = await _call_single(t.get("agent_id", ""), t.get("task", ""))
            results.append(r)
            if "error" in r:
                break  # stop on first error
    elif mode == "parallel":
        coros = [_call_single(t.get("agent_id", ""), t.get("task", "")) for t in tasks]
        results = await asyncio.gather(*coros)
    else:
        return json.dumps(
            {
                "error": f"Unknown mode '{mode}'. Supported: 'sequential', 'parallel'.",
            },
            ensure_ascii=False,
        )

    return json.dumps(results, ensure_ascii=False, indent=2)


dispatch_tool_def = Tool(
    name="dispatch",
    description=(
        "Dispatch multiple tasks to agents in sequential or parallel mode. "
        "Sequential: execute one by one, stop on first error. "
        "Parallel: execute all concurrently. "
        "Returns a JSON array of per-agent results."
    ),
    parameters={
        "tasks": {
            "type": "array",
            "required": True,
            "description": (
                "List of {agent_id, task} objects. "
                "Example: [{\"agent_id\": \"backend\", \"task\": \"write login API\"}, "
                "{\"agent_id\": \"frontend\", \"task\": \"build login page\"}]"
            ),
            "items": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "task": {"type": "string"},
                },
            },
        },
        "mode": {
            "type": "string",
            "required": False,
            "description": "'sequential' (default) or 'parallel'",
            "default": "sequential",
        },
    },
    returns="string: JSON-encoded results array",
    category="team",
)


# ── parallel (shortcut for dispatch with mode="parallel") ──

async def parallel(tasks: List[Dict[str, str]]) -> str:
    """Run multiple tasks simultaneously across different agents.

    Shortcut for dispatch(tasks, mode='parallel').

    Args:
        tasks: List of {"agent_id": str, "task": str} objects.

    Returns:
        JSON-encoded list of results (same as dispatch).
    """
    return await dispatch(tasks, mode="parallel")


parallel_tool_def = Tool(
    name="parallel",
    description=(
        "Run multiple tasks simultaneously across different agents. "
        "Shortcut for dispatch(tasks, mode='parallel'). "
        "Returns a JSON array of per-agent results."
    ),
    parameters={
        "tasks": {
            "type": "array",
            "required": True,
            "description": (
                "List of {agent_id, task} objects. "
                "All tasks run concurrently."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "task": {"type": "string"},
                },
            },
        },
    },
    returns="string: JSON-encoded results array",
    category="team",
)
