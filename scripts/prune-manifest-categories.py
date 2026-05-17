#!/usr/bin/env python3
"""
One-off: prune unused categories from already-built version manifests.

The build now emits only the categories actually referenced by at least one
notebook (see lib/notebooks.py:generate_version_manifest), but versions that
were built before that change still carry the full 9-category list in their
manifest. Running this script rewrites those manifests in place so we don't
have to wait for each version's `.build-ok` to invalidate via a real change.

Notebooks, outputs, and api.json are not touched.

Usage:
    python scripts/prune-manifest-categories.py             # apply
    python scripts/prune-manifest-categories.py --dry-run   # preview
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def prune(manifest_path: Path, dry_run: bool) -> tuple[int, int]:
    """Return (before, after) category count for this manifest."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    notebooks = manifest.get("notebooks", [])
    categories = manifest.get("categories", [])
    used_ids = {n["category"] for n in notebooks}
    pruned = [c for c in categories if c["id"] in used_ids]

    before, after = len(categories), len(pruned)
    if before == after:
        return before, after

    if not dry_run:
        manifest["categories"] = pruned
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")
    return before, after


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    total_before = total_after = touched = 0
    for manifest_path in sorted(STATIC_DIR.glob("*/v*/manifest.json")):
        before, after = prune(manifest_path, args.dry_run)
        rel = manifest_path.relative_to(STATIC_DIR.parent)
        if before != after:
            touched += 1
            print(f"  {rel}: {before} → {after} categories")
        total_before += before
        total_after += after

    action = "would prune" if args.dry_run else "pruned"
    print(f"\n{touched} manifest(s) {action}, total categories {total_before} → {total_after}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
