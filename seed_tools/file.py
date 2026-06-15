"""File read/search tools"""
import fnmatch
import glob
import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

from seed.core.models import Tool
from seed_tools.artifact_helpers import (
    _artifact_summary,
    _artifact_write_text,
    _summarize_text_with_fallback,
)
from seed_tools.shell_helpers import _active_agent_and_session, _env_truthy

logger = logging.getLogger(__name__)


def _file_read_line_window(filepath: str, start_line: int, limit: int, max_bytes: int) -> str:
    """Read up to ``limit`` lines starting at 1-based ``start_line`` (inclusive)."""
    lines_out: List[str] = []
    line_no = 0
    bytes_used = 0
    truncated_bytes = False
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_no += 1
            if line_no < start_line:
                continue
            b = len(line.encode("utf-8", errors="replace"))
            if bytes_used + b > max_bytes:
                truncated_bytes = True
                break
            bytes_used += b
            lines_out.append(line)
            if limit > 0 and len(lines_out) >= limit:
                break
    content = "".join(lines_out)
    meta_tail = ""
    if truncated_bytes:
        meta_tail = f"\n...[file bytes truncated at {max_bytes}]"
    if not lines_out:
        return f"Error: start={start_line} is beyond end of file (file has {line_no} lines)"
    ap = _artifact_write_text(kind="file_read", name_hint=os.path.basename(filepath), text=content)
    if ap:
        return _artifact_summary(title=f"[file_read] {filepath} (lines {start_line}+)", text=content, path=ap) + meta_tail
    return content + meta_tail


def file_read_handler(filepath: str, limit: int = 1000, start: int = 1) -> str:
    """Read contents of a file. ``start`` is 1-based line number to begin from (inclusive)."""
    try:
        if not os.path.exists(filepath):
            return f"Error: File not found: {filepath}"
        start_line = max(1, int(start))
        try:
            max_bytes = int(os.environ.get("SEED_FILE_READ_MAX_BYTES", "2097152") or 2097152)
        except Exception:
            max_bytes = 2097152
        max_bytes = max(64 * 1024, min(max_bytes, 200 * 1024 * 1024))

        if start_line > 1:
            return _file_read_line_window(filepath, start_line, limit, max_bytes)
        # Adaptive mode:
        # - Small files: return content (optionally artifact summary).
        # - Large files: stream chunks, persist full text as artifact, return rolling summary.
        summarize_on = _env_truthy("SEED_FILE_READ_CHUNK_SUMMARY", "1")
        try:
            threshold_chars = int(os.environ.get("SEED_FILE_READ_CHUNK_SUMMARY_THRESHOLD_CHARS", "30000") or 30000)
        except Exception:
            threshold_chars = 30000
        try:
            chunk_chars = int(os.environ.get("SEED_FILE_READ_CHUNK_CHARS", "30000") or 30000)
        except Exception:
            chunk_chars = 30000
        try:
            max_chunks = int(os.environ.get("SEED_FILE_READ_MAX_CHUNKS", "12") or 12)
        except Exception:
            max_chunks = 12
        try:
            summary_max_tokens = int(os.environ.get("SEED_FILE_READ_SUMMARY_MAX_TOKENS", "1200") or 1200)
        except Exception:
            summary_max_tokens = 1200
        try:
            roll_max_chars = int(os.environ.get("SEED_FILE_READ_ROLLING_SUMMARY_CHARS", "2000") or 2000)
        except Exception:
            roll_max_chars = 2000

        threshold_chars = max(2000, min(threshold_chars, 400_000))
        chunk_chars = max(2000, min(chunk_chars, 200_000))
        max_chunks = max(1, min(max_chunks, 200))
        summary_max_tokens = max(128, min(summary_max_tokens, 8192))
        roll_max_chars = max(200, min(roll_max_chars, 20_000))

        # Prepare an artifact file for the raw text (streamed, no large in-memory buffer).
        raw_path: Optional[str] = None
        raw_fp = None
        try:
            if _env_truthy("SEED_TOOL_ARTIFACTS", "1"):
                from seed.core.llm_sess import agent_sessions_dir

                agent_id, session_id = _active_agent_and_session()
                base = os.path.join(str(agent_sessions_dir(agent_id)), "_artifacts", session_id)
                os.makedirs(base, exist_ok=True)
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                safe = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in os.path.basename(filepath))[:64]
                raw_path = os.path.join(base, f"{ts}_file_read_{safe}.txt")
                raw_fp = open(raw_path, "w", encoding="utf-8", errors="replace")
        except Exception:
            raw_path = None
            raw_fp = None

        prefix_buf: List[str] = []
        prefix_len = 0
        summary = ""
        in_chunk_summary = False
        chunk_buf: List[str] = []
        chunk_len = 0
        chunks_done = 0
        bytes_used = 0
        truncated = False
        lines_seen = 0

        def _flush_chunk_into_summary(chunk_text: str) -> None:
            nonlocal summary, chunks_done
            if not summarize_on:
                return
            if not chunk_text.strip():
                return
            if chunks_done >= max_chunks:
                return
            if not summary.strip():
                summary = _summarize_text_with_fallback(text=chunk_text, max_tokens=summary_max_tokens)
            else:
                merged_in = (
                    "当前摘要（请保持其不变或进一步压缩）：\n"
                    + summary.strip()[:roll_max_chars]
                    + "\n\n新增内容（请把关键信息合并进摘要）：\n"
                    + chunk_text
                )
                summary = _summarize_text_with_fallback(text=merged_in, max_tokens=summary_max_tokens)
            if len(summary) > roll_max_chars:
                summary = summary[:roll_max_chars].rstrip() + "…"
            chunks_done += 1

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    lines_seen += 1
                    b = len(line.encode("utf-8", errors="replace"))
                    if bytes_used + b > max_bytes:
                        truncated = True
                        break
                    bytes_used += b
                    if raw_fp is not None:
                        try:
                            raw_fp.write(line)
                        except Exception:
                            pass

                    if not in_chunk_summary:
                        if prefix_len < threshold_chars:
                            prefix_buf.append(line)
                            prefix_len += len(line)
                            continue
                        # Switch to chunk summary mode: summarize the prefix first.
                        in_chunk_summary = True
                        _flush_chunk_into_summary("".join(prefix_buf))
                        prefix_buf = []

                    # Now in chunk summary mode: accumulate chunk and flush when big.
                    chunk_buf.append(line)
                    chunk_len += len(line)
                    if chunk_len >= chunk_chars:
                        _flush_chunk_into_summary("".join(chunk_buf))
                        chunk_buf = []
                        chunk_len = 0
                        if chunks_done >= max_chunks:
                            truncated = True
                            break

        finally:
            try:
                if raw_fp is not None:
                    raw_fp.close()
            except Exception:
                pass

        # If we never switched into chunk summary mode, behave like the old implementation (but with bytes cap).
        if not in_chunk_summary:
            content = "".join(prefix_buf)
            lines = content.split("\n")
            if limit and limit > 0 and len(lines) > limit:
                content = "\n".join(lines[:limit]) + f"\n...[{len(lines) - limit} lines truncated]"
            if truncated:
                content = content.rstrip() + f"\n...[file bytes truncated at {max_bytes}]"
            ap = _artifact_write_text(kind="file_read", name_hint=os.path.basename(filepath), text=content)
            if ap:
                return _artifact_summary(title=f"[file_read] {filepath}", text=content, path=ap)
            return content

        # Flush the tail chunk if any.
        if chunk_buf and chunks_done < max_chunks:
            _flush_chunk_into_summary("".join(chunk_buf))

        meta = {
            "ok": True,
            "mode": "chunk_summary",
            "filepath": filepath,
            "saved_to": raw_path,
            "bytes_read": bytes_used,
            "max_bytes": max_bytes,
            "lines_seen": lines_seen,
            "chunks_summarized": chunks_done,
            "max_chunks": max_chunks,
            "truncated": bool(truncated),
            "summary_chars": len(summary or ""),
        }
        return json.dumps(meta, ensure_ascii=False) + "\n\n" + (summary or "").strip()
    except Exception as e:
        return f"Error reading file: {e}"

file_read_def = Tool(
    name="file_read",
    description="Read contents of a file",
    parameters={
        "filepath": {"type": "string", "required": True, "description": "Path to the file to read"},
        "start": {
            "type": "integer",
            "required": False,
            "description": "1-based line number to start reading from (inclusive). Default 1 = file beginning.",
        },
        "limit": {"type": "integer", "required": False, "description": "Maximum lines to return (default: 1000)"},
    },
    returns="string: File contents"
)

# Artifact helper: read a saved long tool output precisely.


# ── File write/edit tools ────────────────────────────────────────────
import re

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
    name="file_edit",
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
def glob_handler(pattern: str, directory: Optional[str] = None, max_results: int = 20) -> List[str]:
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

glob_def = Tool(
    name="glob",
    description="Match file paths against a glob pattern using fnmatch",
    parameters={
        "pattern": {"type": "string", "required": True, "description": "Glob pattern (e.g., '*.py', 'test_*')"},
        "directory": {"type": "string", "required": False, "description": "Directory to search in (default: current directory)"},
        "max_results": {"type": "integer", "required": False, "description": "Maximum results to return (default: 20)"}
    },
    returns="list[str]: Matching file paths"
)

# Claw-code Tool 2: GrepTool - Content search
def grep_handler(pattern: str, directory: Optional[str] = None, max_results: int = 20) -> List[str]:
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

grep_def = Tool(
    name="grep",
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

