#!/usr/bin/env python3
"""
Inspect all notebook outputs under static/ and report failures.

Behaviour (always exits 0 — this is a diagnostic step, not a gate):
- Writes a Markdown summary table to $GITHUB_STEP_SUMMARY (if set) listing
  every failed notebook per package/version with the full captured error.
- Emits ::warning:: log lines so GitHub annotates each failed notebook on the
  Actions run page (annotation text is truncated for legibility).

Workflow gating: build.py exits non-zero when a build crashes outright;
per-notebook execution failures are deliberately not blocking because a
single broken example shouldn't withhold the other healthy versions from
being deployed.

Usage (called from CI):
    python scripts/check-notebook-health.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Skip directories under static/ that aren't packages.
NON_PACKAGE_DIRS = {"pyodide"}


def _load_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences from a string."""
    out = []
    i = 0
    while i < len(s):
        if s[i] == "\x1b" and i + 1 < len(s) and s[i + 1] == "[":
            j = i + 2
            while j < len(s) and not (0x40 <= ord(s[j]) <= 0x7E):
                j += 1
            i = j + 1
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def collect_failures() -> dict[tuple[str, str], list[tuple[str, str]]]:
    """Return {(package, tag): [(notebook_stem, full_error), ...]} for failed outputs.

    The full error string is preserved; annotation formatting decides on its own
    how much to surface.
    """
    failures: dict[tuple[str, str], list[tuple[str, str]]] = {}

    for pkg_dir in sorted(p for p in STATIC_DIR.iterdir() if p.is_dir()):
        if pkg_dir.name in NON_PACKAGE_DIRS:
            continue
        for version_dir in sorted(p for p in pkg_dir.iterdir() if p.is_dir()):
            if not version_dir.name.startswith("v"):
                continue
            outputs_dir = version_dir / "outputs"
            if not outputs_dir.exists():
                continue
            for output_file in sorted(outputs_dir.glob("*.json")):
                data = _load_json(output_file)
                if data is None or data.get("success") is not False:
                    continue
                error = _strip_ansi(str(data.get("error", "unknown error"))).strip()
                failures.setdefault((pkg_dir.name, version_dir.name), []).append(
                    (output_file.stem, error)
                )
    return failures


def latest_tags() -> dict[str, str]:
    """Return {package_id: latest_tag} from each package's top-level manifest."""
    result: dict[str, str] = {}
    for pkg_dir in STATIC_DIR.iterdir():
        if not pkg_dir.is_dir() or pkg_dir.name in NON_PACKAGE_DIRS:
            continue
        manifest = _load_json(pkg_dir / "manifest.json")
        if manifest and "latestTag" in manifest:
            result[pkg_dir.name] = manifest["latestTag"]
    return result


def main() -> int:
    failures = collect_failures()
    latest = latest_tags()
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")

    if not failures:
        msg = "All notebook outputs report success.\n"
        print(msg, end="")
        if summary_path:
            Path(summary_path).write_text("### Notebook health\n\n" + msg)
        return 0

    # GitHub annotations — single-line, so we strip newlines and trim hard.
    for (pkg, tag), items in failures.items():
        for stem, err in items:
            tail = err.replace("\n", " ⏎ ")
            if len(tail) > 240:
                tail = tail[-240:]  # tail of the traceback is where the real exception sits
            print(f"::warning title=Notebook failure::{pkg}/{tag}/{stem}: ...{tail}")

    # Step summary with the FULL error in a collapsible <details> per notebook
    # so the run page surfaces every traceback in readable form.
    n_failed = sum(len(v) for v in failures.values())
    lines: list[str] = [
        "### Notebook health\n\n",
        f"{n_failed} failed notebook output(s) across {len(failures)} version(s).\n\n",
    ]
    for (pkg, tag), items in sorted(failures.items()):
        is_latest = " (latest)" if latest.get(pkg) == tag else ""
        lines.append(f"#### `{pkg}/{tag}`{is_latest}\n\n")
        for stem, err in items:
            lines.append(f"<details><summary><code>{stem}</code></summary>\n\n")
            lines.append("```\n")
            lines.append(err.rstrip())
            lines.append("\n```\n\n</details>\n\n")

    output = "".join(lines)
    if summary_path:
        Path(summary_path).write_text(output)
    else:
        sys.stdout.write(output)

    latest_failing = sorted({pkg for (pkg, tag) in failures if latest.get(pkg) == tag})
    if latest_failing:
        print(
            f"\nLatest version of {', '.join(latest_failing)} has failed notebooks "
            "(diagnostic only — does not block deployment).",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
