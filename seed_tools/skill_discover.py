"""Tool module: skill_discover — scan agent & project skills by frontmatter."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from seed.core.models import Tool

SKILL_HOME_ENV = "AGENT_HOME"


def _parse_frontmatter(text: str) -> dict:
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n(?:---|\.\.\.)", text, re.DOTALL)
    if not m:
        return meta
    for line in m.group(1).split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key in ("tags",):
            val = [t.strip().strip('"').strip("'") for t in val.strip("[]").split(",") if t.strip()]
        meta[key] = val
    return meta


def _list_skills(base_dir: Path, level: str) -> list[dict]:
    """Scan a single directory for skills (both directory/SKILL.md and flat .md)."""
    if not base_dir.is_dir():
        return []
    results = []
    # Format A: directory/<name>/SKILL.md
    for entry in sorted(base_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        meta = _parse_frontmatter(text)
        if not meta.get("name") and not meta.get("description"):
            # no valid frontmatter, skip
            continue
        results.append({
            "name": meta.get("name", entry.name),
            "description": meta.get("description", ""),
            "tags": meta.get("tags", []),
            "trigger": meta.get("trigger", ""),
            "path": str(skill_md.resolve()),
            "level": level,
            "format": "skill-md-dir",
        })
    # Format B: flat *.md (transitional, will be removed in Wave 4)
    for f in sorted(base_dir.glob("*.md")):
        if f.name == "SKILL.md" or f.name.startswith("."):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        meta = _parse_frontmatter(text)
        results.append({
            "name": meta.get("name", f.stem),
            "description": meta.get("description", ""),
            "tags": meta.get("tags", []),
            "trigger": meta.get("trigger", ""),
            "path": str(f.resolve()),
            "level": level,
            "format": "flat-md",
        })
    return results


def skill_discover(
    scope: str = "all",
    match: str | None = None,
    project_path: str | None = None,
) -> str:
    """Discover skills by scanning agent and/or project skill directories.

    Args:
        scope: "agent", "project", or "all" (default "all")
        match: Optional substring to filter by name/description/tags
        project_path: Path to project directory (required when scope="project")
    """
    results: list[dict] = []
    agent_home_env = os.environ.get("AGENT_HOME")
    agent_home = Path(agent_home_env).resolve() if agent_home_env else \
        Path(__file__).resolve().parent.parent.parent / ".codeagent" / "agents" / "default"

    # Agent-level skills
    if scope in ("agent", "all"):
        agent_skills_dir = agent_home / "skills"
        results.extend(_list_skills(agent_skills_dir, "agent"))

    # Project-level skills
    if scope in ("project", "all") and project_path:
        project_skills_dir = Path(project_path) / ".codeagent" / "default" / "skills"
        results.extend(_list_skills(project_skills_dir, "project"))

    # De-duplicate: project-level overrides agent-level with same name
    seen: dict[str, dict] = {}
    for r in results:
        name = r["name"]
        if name in seen and r["level"] == "project":
            seen[name] = r  # project overrides
        elif name not in seen:
            seen[name] = r
    deduped = list(seen.values())

    # Optional match filter
    if match:
        m_lower = match.lower()
        filtered = []
        for r in deduped:
            if m_lower in r["name"].lower():
                filtered.append(r)
                continue
            if m_lower in r["description"].lower():
                filtered.append(r)
                continue
            if any(m_lower in t.lower() for t in r.get("tags", [])):
                filtered.append(r)
                continue
        deduped = filtered

    # Deduplicate by path to avoid duplicates from flat + dir format overlap
    seen_paths: set[str] = set()
    final: list[dict] = []
    for r in deduped:
        if r["path"] not in seen_paths:
            seen_paths.add(r["path"])
            final.append(r)

    return json.dumps(final, ensure_ascii=False, indent=2)


skill_discover_def = Tool(
    name="skill_discover",
    description=(
        "Discover skills by scanning agent and/or project skill directories. "
        "Returns a JSON array of {name, description, tags, trigger, path, level, format}. "
        "Use when you need to find a skill — pass match to filter by name, description, or tags."
    ),
    parameters={
        "scope": {
            "type": "string",
            "required": False,
            "description": '"agent" | "project" | "all" (default "all")',
        },
        "match": {
            "type": "string",
            "required": False,
            "description": "Optional substring to filter by name/description/tags",
        },
        "project_path": {
            "type": "string",
            "required": False,
            "description": "Path to project directory (required when scope='project')",
        },
    },
    returns="string",
)
