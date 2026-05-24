"""File write/edit tools"""
import fnmatch
import glob
import logging
import os
import re
from typing import List, Optional

from seed.core.models import Tool

logger = logging.getLogger(__name__)

_SEARCH_SKIP_DIR_NAMES = frozenset({
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".next",
    ".nuxt",
    "coverage",
})

_SEARCH_SKIP_FILE_SUFFIXES = (".min.js", ".min.css", ".map")
_GREP_MAX_LINE_CHARS = 500
_GREP_MAX_FILE_BYTES = 512 * 1024


def _path_has_skip_segment(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(f"/{name}/" in normalized or normalized.endswith(f"/{name}") for name in _SEARCH_SKIP_DIR_NAMES)


def _prune_walk_dirs(dirs: List[str]) -> None:
    dirs[:] = [d for d in dirs if d not in _SEARCH_SKIP_DIR_NAMES]


def _should_skip_search_file(filename: str) -> bool:
    lower = filename.lower()
    return any(lower.endswith(suffix) for suffix in _SEARCH_SKIP_FILE_SUFFIXES)


def _format_grep_match(filepath: str, line_num: int, line_content: str) -> str:
    line = line_content.strip()
    if len(line) > _GREP_MAX_LINE_CHARS:
        drop = len(line) - _GREP_MAX_LINE_CHARS
        line = line[:_GREP_MAX_LINE_CHARS] + f"...[line truncated {drop} chars]"
    return f"{filepath}:{line_num}:{line}"

def file_write_handler(filepath: str, content: str, mode: str = "overwrite") -> str:
    """Write content to a file"""
    try:
        parent_dir = os.path.dirname(filepath)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        write_mode = 'w' if mode == "overwrite" else ('a' if mode == "append" else 'w')
        with open(filepath, write_mode, encoding='utf-8') as f:
            f.write(content)
        mode_str = "appended to" if mode == "append" else "wrote to"
        return f"Successfully {mode_str} {filepath} ({len(content)} bytes)"
    except Exception as e:
        return f"Error writing file: {e}"

file_write_def = Tool(
    name="file_write",
    description="Write content to a file",
    parameters={
        "filepath": {"type": "string", "required": True, "description": "Path to the file to write"},
        "content": {
            "type": "string",
            "required": True,
            "allow_empty": True,
            "description": "Content to write (may be empty to truncate/create empty file)",
        },
        "mode": {"type": "string", "required": False, "description": "Mode: 'overwrite' or 'append' (default: overwrite)"}
    },
    returns="string: Success message"
)

# Core MVP Tool 7: file_search
def file_edit_handler(filepath: str, old_text: str, new_text: str, allow_regex: bool = False) -> str:
    """Replace text in a file"""
    try:
        import re
        import os
        
        if not os.path.exists(filepath):
            return f"Error: File not found: {filepath}"
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if allow_regex:
            new_content = re.sub(old_text, new_text, content)
        else:
            new_content = content.replace(old_text, new_text)
        
        if new_content == content:
            return f"No replacements made for '{old_text[:50]}...' in {filepath}"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return f"Successfully replaced '{old_text[:50]}...' with '{new_text[:50]}...' in {filepath}"
    except Exception as e:
        return f"Error editing file: {e}"

file_edit_def = Tool(
    name="file_edit_tool",
    description="Replace text in a file (supports regex)",
    parameters={
        "filepath": {"type": "string", "required": True, "description": "Path to the file to edit"},
        "old_text": {"type": "string", "required": True, "description": "Text to find"},
        "new_text": {
            "type": "string",
            "required": True,
            "allow_empty": True,
            "description": "Replacement text (may be empty to delete old_text)",
        },
        "allow_regex": {"type": "boolean", "required": False, "description": "Treat old_text as a regex pattern", "default": False}
    },
    returns="string: Success/error message"
)

# Todo management: unified tool with operation parameter
def glob_tool_handler(pattern: str, directory: Optional[str] = None, max_results: int = 20) -> List[str]:
    """Match file paths against a glob pattern using fnmatch"""
    try:
        dir_path = directory or os.getcwd()
        matches = []
        for root, dirs, files in os.walk(dir_path):
            _prune_walk_dirs(dirs)
            for filename in files:
                if _should_skip_search_file(filename):
                    continue
                if fnmatch.fnmatch(filename, pattern):
                    full_path = os.path.abspath(os.path.join(root, filename))
                    if _path_has_skip_segment(full_path):
                        continue
                    matches.append(full_path)
                    if len(matches) >= max_results:
                        break
            if len(matches) >= max_results:
                break
        return matches[:max_results]
    except Exception:
        return []

glob_tool_def = Tool(
    name="glob_tool",
    description="Match file paths against a glob pattern using fnmatch",
    parameters={
        "pattern": {"type": "string", "required": True, "description": "Glob pattern (e.g., '*.py', 'test_*')"},
        "directory": {"type": "string", "required": False, "description": "Directory to search in (default: current directory)"},
        "max_results": {"type": "integer", "required": False, "description": "Maximum results to return (default: 20)"}
    },
    returns="list[str]: Matching file paths"
)

# Claw-code Tool 2: GrepTool - Content search
def grep_tool_handler(pattern: str, directory: Optional[str] = None, max_results: int = 20) -> List[str]:
    """Search for content matching a regex pattern"""
    try:
        dir_path = directory or os.getcwd()
        results = []
        compiled = re.compile(pattern, re.MULTILINE)

        for root, dirs, files in os.walk(dir_path):
            _prune_walk_dirs(dirs)
            for filename in files:
                if not (filename.endswith(".py") or filename.endswith(".js") or filename.endswith(".ts")):
                    continue
                if _should_skip_search_file(filename):
                    continue
                filepath = os.path.join(root, filename)
                if _path_has_skip_segment(filepath):
                    continue
                try:
                    if os.path.getsize(filepath) > _GREP_MAX_FILE_BYTES:
                        continue
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    lines = content.split("\n")
                    for match in compiled.finditer(content):
                        line_num = content[: match.start()].count("\n") + 1
                        line_content = lines[line_num - 1] if 0 < line_num <= len(lines) else ""
                        results.append(_format_grep_match(filepath, line_num, line_content))
                        if len(results) >= max_results:
                            break
                except Exception:
                    pass
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        return [f"Error searching content: {e}"]

grep_tool_def = Tool(
    name="grep_tool",
    description="Search for content matching a regex pattern",
    parameters={
        "pattern": {"type": "string", "required": True, "description": "Regex pattern to search for"},
        "directory": {"type": "string", "required": False, "description": "Directory to search in (default: current directory)"},
        "max_results": {"type": "integer", "required": False, "description": "Maximum results to return (default: 20)"}
    },
    returns="list[str]: Matching file lines with context"
)

# Claw-code Tool 3: FileEditorTool - File editing
def file_search_handler(pattern: str, directory: str = ".", max_results: int = 20) -> List[str]:
    """Search for files matching a glob pattern"""
    try:
        search_path = os.path.join(directory, pattern)
        matching_files = glob.glob(search_path, recursive=True)
        filtered = []
        for path in matching_files:
            abs_path = os.path.abspath(path)
            if _path_has_skip_segment(abs_path):
                continue
            filtered.append(abs_path)
            if len(filtered) >= max_results:
                break
        return filtered[:max_results]
    except Exception as e:
        return [f"Error searching files: {e}"]

file_search_def = Tool(
    name="file_search",
    description="Search for files matching a glob pattern",
    parameters={
        "pattern": {"type": "string", "required": True, "description": "Glob pattern (e.g., '*.py', 'test_*')"},
        "directory": {"type": "string", "required": False, "description": "Directory to search in (default: current directory)"},
        "max_results": {"type": "integer", "required": False, "description": "Maximum results to return (default: 20)"}
    },
    returns="list[str]: Matching file paths"
)

