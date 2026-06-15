"""Tool registration helpers"""
from dataclasses import replace
import logging

from seed.core.models import Tool
from seed.core.tool_runtime import ToolExecutor, ToolRegistry

logger = logging.getLogger(__name__)

# ── Import all tool modules ──
from seed_tools.misc import (
    echo_tool, echo_tool_def, calculate_tool, calc_tool_def,
    counter_tool, counter_tool_def, whoami_tool, whoami_tool_def,
    wbs_draft_tool, wbs_def, workspace_verify_handler, workspace_verify_def,
)
from seed_tools.file import file_read_handler, file_read_def
from seed_tools.file import (
    file_write_handler, file_write_def, file_edit_handler, file_edit_def,
    file_search_handler, file_search_def, glob_handler, glob_def,
    grep_handler, grep_def,
)
from seed_tools.artifact import artifact_read_handler, artifact_read_def
from seed_tools.web import web_fetch_handler, web_fetch_def, web_search_handler, web_search_def
from seed_tools.code_check import (
    code_analyze_handler,
    code_analyze_def,
    code_check_handler,
    code_check_def,
)
from seed_tools.todo import todo_handler, todo_def
from seed_tools.tool_search import tool_search_handler, tool_search_def
from seed_tools.notebook import notebook_edit_handler, notebook_edit_def
from seed_tools.memory_search import memory_search_handler, memory_search_def
from seed_tools.self_reflect import self_reflect_tool, reflect_def
from seed_tools.cron import (
    codeagent_cron_path_def,
    codeagent_cron_path_handler,
    codeagent_cron_reload_def,
    codeagent_cron_reload_handler,
    seed_cron_path_def,
    seed_cron_path_handler,
    seed_cron_reload_def,
    seed_cron_reload_handler,
)
from seed_tools.cron import (
    codeagent_cron_apply_def,
    codeagent_cron_apply_handler,
    seed_cron_apply_def,
    seed_cron_apply_handler,
)
from seed_tools.hub import hub_send, hub_send_def
from seed_tools.team import (
    call_agent, call_agent_tool_def,
    dispatch, dispatch_tool_def,
    parallel, parallel_tool_def,
)
from seed_tools.git import git_handler
from seed_tools.vision import (
    vision_analyze,
    vision_analyze_def,
    vision_analyze_directory,
    vision_analyze_directory_def,
)
from seed_tools.image_gen import image_generate, image_generate_def
from seed_tools.music_gen import music_generate, music_generate_def
from seed_tools.video_gen import video_generate, video_generate_def
from seed_tools.media import (
    attachment_resolve_path,
    attachment_resolve_path_def,
    audio_transcribe,
    audio_transcribe_def,
    video_analyze,
    video_analyze_def,
)
from seed_tools.browser import (
    browser_status,
    browser_status_def,
    browser_connect,
    browser_connect_def,
    browser_ensure_running,
    browser_ensure_running_def,
    browser_targets,
    browser_targets_def,
    browser_new_page,
    browser_new_page_def,
    browser_navigate,
    browser_navigate_def,
    browser_screenshot,
    browser_screenshot_def,
)
from seed_tools.bash import bash_def, bash_handler

# ── Migrated tool_modules tools ──
from seed_tools.refactor import refactor_handler, refactor_tool_def
from seed_tools.diagram import diagram_handler, diagram_tool_def
from seed_tools.api_docs import api_docs_handler, api_docs_tool_def
from seed_tools.scaffold import scaffold_handler, scaffold_tool_def
from seed_tools.project import project_handler, project_tool_def
from seed_tools.db import db_handler, db_tool_def
from seed_tools.deps_check import deps_check_handler, deps_check_tool_def
from seed_tools.test_gen import test_gen_handler, test_gen_tool_def
from seed_tools.test_run import test_run_handler, test_run_def
from seed_tools.symbol import (
    symbol_index_refresh_def,
    symbol_index_refresh_handler,
    symbol_search_def,
    symbol_search_handler,
)
from seed_tools.lsp import (
    lsp_definition_def,
    lsp_definition_handler,
    lsp_diagnostics_def,
    lsp_diagnostics_handler,
)
from seed_tools.patch import apply_patch_def, apply_patch_handler
from seed_tools.mcp import (
    mcp_call_def,
    mcp_call_handler,
    mcp_list_tools_def,
    mcp_list_tools_handler,
    mcp_servers_def,
    mcp_servers_handler,
)
from seed_tools.pipeline import pipeline_handler, pipeline_tool_def
from seed_tools.instruction import instruction_read_def, instruction_read_handler
from seed_tools.deploy import deploy_handler, deploy_tool_def

# ── Create missing tool definitions ──
git_tool_def = Tool(
    name="git",
    description="Git operations tool",
    parameters={
        "command": {"type": "string", "required": True, "description": "Git subcommand"},
        "args": {"type": "string", "required": False, "description": "Arguments"},
        "message": {"type": "string", "required": False, "description": "Commit message"},
    },
    returns="string",
    category="git",
)


def setup_builtin_tools():
    """Setup and register all builtin tools."""
    registry = ToolRegistry()
    
    # Misc tools
    registry.register(echo_tool_def, echo_tool)
    registry.register(calc_tool_def, calculate_tool)
    registry.register(counter_tool_def, counter_tool)
    registry.register(whoami_tool_def, whoami_tool)
    registry.register(wbs_def, wbs_draft_tool)
    registry.register(workspace_verify_def, workspace_verify_handler)

    # Shell (bash + bash alias for prompts / acquired-tool policy)
    registry.register(bash_def, bash_handler)

    # File tools
    registry.register(file_read_def, file_read_handler)
    registry.register(file_write_def, file_write_handler)
    registry.register(file_edit_def, file_edit_handler)
    registry.register(file_search_def, file_search_handler)
    registry.register(glob_def, glob_handler)
    registry.register(grep_def, grep_handler)
    
    # Artifact tools
    registry.register(artifact_read_def, artifact_read_handler)
    
    # Web tools
    registry.register(web_fetch_def, web_fetch_handler)
    registry.register(web_search_def, web_search_handler)
    
    # Code tools
    registry.register(code_check_def, code_check_handler)
    registry.register(code_analyze_def, code_analyze_handler)
    
    # Todo tools
    registry.register(todo_def, todo_handler)
    
    # Search tools
    registry.register(tool_search_def, tool_search_handler)
    
    # Notebook tools
    registry.register(notebook_edit_def, notebook_edit_handler)
    
    # Memory tools
    registry.register(memory_search_def, memory_search_handler)
    registry.register(reflect_def, self_reflect_tool)
    
    # Cron tools
    registry.register(seed_cron_path_def, seed_cron_path_handler)
    registry.register(seed_cron_reload_def, seed_cron_reload_handler)
    registry.register(seed_cron_apply_def, seed_cron_apply_handler)
    registry.register(codeagent_cron_path_def, codeagent_cron_path_handler)
    registry.register(codeagent_cron_reload_def, codeagent_cron_reload_handler)
    registry.register(codeagent_cron_apply_def, codeagent_cron_apply_handler)
    
    # Git tool
    registry.register(git_tool_def, git_handler)
    
    # Hub tools
    registry.register(hub_send_def, hub_send)

    # Team tools
    registry.register(call_agent_tool_def, call_agent)
    registry.register(dispatch_tool_def, dispatch)
    registry.register(parallel_tool_def, parallel)
    
    # Browser tools
    registry.register(browser_status_def, browser_status)
    registry.register(browser_connect_def, browser_connect)
    registry.register(browser_ensure_running_def, browser_ensure_running)
    registry.register(browser_targets_def, browser_targets)
    registry.register(browser_new_page_def, browser_new_page)
    registry.register(browser_navigate_def, browser_navigate)
    registry.register(browser_screenshot_def, browser_screenshot)

    registry.register(vision_analyze_def, vision_analyze)
    registry.register(vision_analyze_directory_def, vision_analyze_directory)
    registry.register(image_generate_def, image_generate)
    registry.register(music_generate_def, music_generate)
    registry.register(video_generate_def, video_generate)
    registry.register(attachment_resolve_path_def, attachment_resolve_path)
    registry.register(audio_transcribe_def, audio_transcribe)
    registry.register(video_analyze_def, video_analyze)

    # ── Migrated tool_modules (dev tools) ──
    registry.register(project_tool_def, project_handler)
    registry.register(refactor_tool_def, refactor_handler)
    registry.register(scaffold_tool_def, scaffold_handler)
    registry.register(test_gen_tool_def, test_gen_handler)
    registry.register(test_run_def, test_run_handler)

    # MCP bridge
    registry.register(mcp_servers_def, mcp_servers_handler)
    registry.register(mcp_list_tools_def, mcp_list_tools_handler)
    registry.register(mcp_call_def, mcp_call_handler)

    # Code intelligence (Phase 4)
    registry.register(symbol_search_def, symbol_search_handler)
    registry.register(symbol_index_refresh_def, symbol_index_refresh_handler)
    registry.register(lsp_definition_def, lsp_definition_handler)
    registry.register(lsp_diagnostics_def, lsp_diagnostics_handler)
    registry.register(apply_patch_def, apply_patch_handler)
    registry.register(deploy_tool_def, deploy_handler)
    registry.register(deps_check_tool_def, deps_check_handler)
    registry.register(api_docs_tool_def, api_docs_handler)
    registry.register(diagram_tool_def, diagram_handler)
    registry.register(pipeline_tool_def, pipeline_handler)
    registry.register(db_tool_def, db_handler)

    # Instruction releases (taskagent)
    registry.register(instruction_read_def, instruction_read_handler)
    
    executor = ToolExecutor(registry)
    return registry, executor

