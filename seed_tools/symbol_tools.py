"""Symbol index search and refresh."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from seed.core.models import Tool


def _resolve_root(path: Optional[str]) -> Path:
    if path and str(path).strip():
        return Path(path).expanduser().resolve()
    return Path.cwd().resolve()


def symbol_search_handler(
    query: str,
    path: str = ".",
    kind: str = "all",
    limit: int = 25,
) -> str:
    from seed.integrations.symbol_index import (
        build_symbol_index,
        load_cached_index,
        search_symbols,
    )

    root = _resolve_root(path)
    index = load_cached_index(root)
    if index is None or index.root != str(root):
        index = build_symbol_index(root, use_ctags=True)
    hits = search_symbols(index, query, kind=(kind or "all").strip().lower(), limit=max(1, int(limit)))
    if not hits:
        return f"No symbols matching {query!r} under {root}"
    lines = [f"Symbol matches ({len(hits)}) under {root}:"]
    for h in hits:
        loc = f"{h.path}:{h.line}"
        extra = f" [{h.kind}]"
        if h.container:
            extra += f" in {h.container}"
        if h.signature:
            extra += f" — {h.signature}"
        lines.append(f"- {h.name}{extra} @ {loc}")
    return "\n".join(lines)


def symbol_index_refresh_handler(path: str = ".", use_ctags: bool = True) -> str:
    from seed.integrations.symbol_index import build_symbol_index, save_index_cache

    root = _resolve_root(path)
    index = build_symbol_index(root, use_ctags=bool(use_ctags))
    cache = save_index_cache(index)
    return f"Indexed {len(index.symbols)} symbols under {root}\nCache: {cache}"


symbol_search_def = Tool(
    name="symbol_search",
    description="Search project symbols (functions, classes, methods) by name or path fragment",
    parameters={
        "query": {"type": "string", "required": True, "description": "Symbol or path substring"},
        "path": {"type": "string", "required": False, "description": "Project root (default: cwd)"},
        "kind": {
            "type": "string",
            "required": False,
            "description": "all | function | class | method",
            "default": "all",
        },
        "limit": {"type": "integer", "required": False, "description": "Max results", "default": 25},
    },
    returns="string",
    category="code",
)

symbol_index_refresh_def = Tool(
    name="symbol_index_refresh",
    description="Rebuild symbol index (Python AST + optional ctags) and save to .seed/symbol_index.json",
    parameters={
        "path": {"type": "string", "required": False, "description": "Project root"},
        "use_ctags": {
            "type": "boolean",
            "required": False,
            "description": "Use universal-ctags when available",
            "default": True,
        },
    },
    returns="string",
    category="code",
)
