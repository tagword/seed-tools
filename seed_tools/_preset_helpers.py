"""Common preset resolution helpers for seed-tools multimedia tools.

Replaces the thin wrapper layer previously in ``codeagent.core.*_models``
so that seed-tools depends only on ``seed.core``, not on any host product.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Optional


def resolve_capability_preset(
    capability_key: str,
    env_var: str,
    get_active_fn: Callable[[], str],
    error_desc: str,
) -> dict[str, Any]:
    """Resolve a preset by capability flag.

    Resolution order:
    1. Preset id from ``get_active_fn()`` (context var, set by Web UI / bootstrap)
    2. Preset id from ``env_var`` (fallback env override)
    3. If no id specified: the **single** preset matching ``capability_key``
    4. If multiple match: error asking to disambiguate via env var
    5. If none match: error

    Returns a **copy** of the matched preset dict (safe to mutate).
    """
    from seed.core.llm_presets import load_presets

    pid = get_active_fn() or os.environ.get(env_var, "").strip()

    if pid:
        for p in load_presets():
            if str(p.get("id") or "").strip() == pid:
                if p.get(capability_key) is True:
                    return dict(p)
                raise ValueError(
                    f"preset {pid!r} does not support {capability_key}"
                )
        raise ValueError(f"{error_desc}: preset not found: {pid}")

    # No id specified — find the single matching preset
    matching = [p for p in load_presets() if p.get(capability_key) is True]
    if len(matching) == 1:
        return dict(matching[0])
    if len(matching) > 1:
        raise ValueError(
            f"{error_desc}: multiple presets support {capability_key}, "
            f"set {env_var} to disambiguate"
        )
    raise ValueError(
        f"{error_desc}: no preset with {capability_key}=True found"
    )


def resolve_preset_by_id(preset_id: str) -> Optional[dict[str, Any]]:
    """Look up a preset by exact id match. Returns copy or None."""
    from seed.core.llm_presets import load_presets

    pid = (preset_id or "").strip()
    if not pid:
        return None
    for p in load_presets():
        if str(p.get("id") or "").strip() == pid:
            return dict(p)
    return None
