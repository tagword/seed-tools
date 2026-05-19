"""LSP-backed definition and diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from seed.core.models import Tool


def lsp_definition_handler(
    filepath: str,
    line: int,
    column: int = 0,
    project_root: str = "",
) -> str:
    from seed.core.config_plane import project_root as default_root
    from seed.integrations.lsp_client import LSPError, format_location, get_lsp_session, lsp_enabled
    from seed.integrations.lsp_config import server_for_filepath
    from seed.integrations.symbol_index import python_definition_at

    fp = Path(filepath).expanduser().resolve()
    if not fp.is_file():
        return f"File not found: {filepath}"

    root = Path(project_root).expanduser().resolve() if project_root.strip() else default_root()

    fallback_note = ""
    if lsp_enabled():
        cfg = server_for_filepath(fp, base=root)
        if cfg:
            try:
                locs = get_lsp_session(cfg, root).definition(fp, int(line), int(column))
                if locs:
                    return "Definitions:\n" + "\n".join(
                        f"- {format_location(loc)}" for loc in locs
                    )
            except LSPError as e:
                fallback_note = f"LSP failed ({e}); trying AST fallback.\n"
        else:
            fallback_note = "No LSP server for this file type; AST fallback.\n"
    else:
        fallback_note = "LSP disabled; AST fallback.\n"

    ent = python_definition_at(fp, int(line), int(column))
    if ent:
        return (
            fallback_note
            + f"Definition: {ent.name} ({ent.kind}) at {ent.path}:{ent.line}"
        )
    return fallback_note + "No definition found."


def lsp_diagnostics_handler(filepath: str, project_root: str = "") -> str:
    from seed.core.config_plane import project_root as default_root
    from seed.integrations.lsp_client import (
        LSPError,
        get_lsp_session,
        lsp_enabled,
        pyright_cli_diagnostics,
    )
    from seed.integrations.lsp_config import server_for_filepath

    fp = Path(filepath).expanduser().resolve()
    if not fp.is_file():
        return f"File not found: {filepath}"
    root = Path(project_root).expanduser().resolve() if project_root.strip() else default_root()

    lines: list[str] = []

    if lsp_enabled():
        cfg = server_for_filepath(fp, base=root)
        if cfg:
            try:
                diags = get_lsp_session(cfg, root).diagnostics_pull(fp)
                if diags:
                    lines.append("LSP diagnostics:")
                    for d in diags[:40]:
                        if not isinstance(d, dict):
                            continue
                        sev = d.get("severity", "?")
                        msg = d.get("message", "")
                        rng = d.get("range") or {}
                        st = (rng.get("start") or {}).get("line", 0)
                        lines.append(f"  [{sev}] line {int(st)+1}: {msg}")
            except LSPError as e:
                lines.append(f"LSP diagnostics unavailable: {e}")

    ok, out = pyright_cli_diagnostics(fp, cwd=root)
    if out.strip():
        lines.append("pyright --outputjson:")
        try:
            data = json.loads(out)
            general = data.get("generalDiagnostics") or []
            for d in general[:40]:
                lines.append(
                    f"  {d.get('file','')}:{d.get('range',{}).get('start',{}).get('line',0)+1}: "
                    f"{d.get('message','')}"
                )
        except json.JSONDecodeError:
            lines.append(out[:8000])

    if not lines:
        from seed_tools.code_check_tool import code_check_tool

        lines.append(code_check_tool(filepath=str(fp), language="auto", fix=False))

    return "\n".join(lines) if lines else "No diagnostics."


lsp_definition_def = Tool(
    name="lsp_definition",
    description="Go to definition at line:column (LSP if configured, else Python AST)",
    parameters={
        "filepath": {"type": "string", "required": True},
        "line": {"type": "integer", "required": True},
        "column": {"type": "integer", "required": False, "default": 0},
        "project_root": {"type": "string", "required": False, "description": "Workspace root for LSP"},
    },
    returns="string",
    category="code",
)

lsp_diagnostics_def = Tool(
    name="lsp_diagnostics",
    description="File diagnostics via LSP pull, pyright CLI, or code_check fallback",
    parameters={
        "filepath": {"type": "string", "required": True},
        "project_root": {"type": "string", "required": False},
    },
    returns="string",
    category="code",
)
