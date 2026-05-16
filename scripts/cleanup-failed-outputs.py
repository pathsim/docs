#!/usr/bin/env python3
"""
One-off cleanup: remove notebook output JSONs that recorded a failed execution.

These outputs were generated in environments that can't actually run the
notebooks (older local builds on a Windows box with the wrong Python, batt
notebooks before pathsim-batt was a CI dependency, etc.). Without this
cleanup, those `success: false` files persist forever and the build-ok
marker logic keeps re-running them — that's correct, but a one-time sweep
is faster than waiting 6h for the next CI cron to do it incrementally.

Notebooks (`notebooks/*.ipynb`) and `api.json` are NOT touched. Only the
`outputs/*.json` files that recorded failure are removed. The next build
will regenerate them.

Usage:
    python scripts/cleanup-failed-outputs.py             # apply
    python scripts/cleanup-failed-outputs.py --dry-run   # preview only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def find_failed_outputs(static_dir: Path) -> list[Path]:
    """Return all outputs/*.json files whose success flag is False."""
    failed: list[Path] = []
    for output_file in static_dir.glob("*/v*/outputs/*.json"):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ! could not read {output_file}: {e}", file=sys.stderr)
            continue
        if data.get("success") is False:
            failed.append(output_file)
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted, change nothing.",
    )
    args = parser.parse_args()

    if not STATIC_DIR.exists():
        print(f"static/ not found at {STATIC_DIR}", file=sys.stderr)
        return 1

    failed = find_failed_outputs(STATIC_DIR)

    if not failed:
        print("No failed outputs found — nothing to clean up.")
        return 0

    # Group by version directory for readable reporting.
    by_version: dict[Path, list[Path]] = {}
    for f in failed:
        by_version.setdefault(f.parent.parent, []).append(f)

    total = 0
    for version_dir in sorted(by_version, key=lambda p: p.as_posix()):
        files = by_version[version_dir]
        rel = version_dir.relative_to(STATIC_DIR.parent)
        print(f"\n{rel}  ({len(files)} failed)")
        for f in sorted(files):
            print(f"  - {f.name}")
            if not args.dry_run:
                f.unlink()
            total += 1

    action = "Would remove" if args.dry_run else "Removed"
    print(f"\n{action} {total} failed output file(s) across {len(by_version)} version(s).")
    if args.dry_run:
        print("Re-run without --dry-run to apply.")
    else:
        print("Next CI build (or `python scripts/build.py`) will regenerate them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
