"""
Builtin tools package (``seed-tools`` distribution).

Registry / executor contracts live in ``seed.core.tool_runtime``.
"""

__version__ = "1.0.2"
from seed.core.tool_runtime import ToolExecutionError, ToolExecutor, ToolRegistry

from seed_tools._registration import setup_builtin_tools

__all__ = ("ToolRegistry", "ToolExecutor", "ToolExecutionError", "setup_builtin_tools")
