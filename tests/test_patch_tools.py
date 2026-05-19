"""Unified patch apply."""

from __future__ import annotations

from pathlib import Path

from seed_tools.patch_tools import apply_patch_handler


def test_apply_patch_dry_run(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("line1\nline2\nline3\n", encoding="utf-8")
    patch = """--- a/a.txt
+++ b/a.txt
@@ -2,1 +2,1 @@
 line2
-line2
+line2-changed
"""
    out = apply_patch_handler(patch, dry_run=True, base_path=str(tmp_path))
    assert "DRY-RUN" in out
    assert f.read_text(encoding="utf-8") == "line1\nline2\nline3\n"


def test_apply_patch_writes(tmp_path: Path) -> None:
    f = tmp_path / "b.txt"
    f.write_text("alpha\nbeta\n", encoding="utf-8")
    patch = """--- a/b.txt
+++ b/b.txt
@@ -2,1 +2,1 @@
 beta
-beta
+beta2
"""
    out = apply_patch_handler(patch, dry_run=False, base_path=str(tmp_path))
    assert "APPLIED" in out
    assert "beta2" in f.read_text(encoding="utf-8")
