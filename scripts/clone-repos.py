#!/usr/bin/env python3
"""Clone all PathSim package repositories declared in lib.config.PACKAGES.

Idempotent: skips clone when target directory already exists.
Required repos that fail to clone produce a non-zero exit; optional repos
(``required: False``) only emit a warning. Tags are fetched after each clone
and the latest tag is logged.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.config import PACKAGES, ROOT_DIR  # noqa: E402


def clone(github_repo: str, dest: Path, required: bool) -> bool:
    if dest.exists():
        print(f"✓ {dest.name}: already present")
        return True
    url = f"https://github.com/{github_repo}.git"
    print(f"  Cloning {github_repo} → {dest} ...")
    result = subprocess.run(["git", "clone", url, str(dest)])
    if result.returncode == 0:
        return True
    if required:
        print(f"✗ Failed to clone {github_repo} (required)")
        return False
    print(f"⊘ Skipping {github_repo} (not available)")
    return True


def fetch_tags(dest: Path) -> None:
    if not dest.exists():
        return
    subprocess.run(["git", "-C", str(dest), "fetch", "--tags"], check=False)
    result = subprocess.run(
        ["git", "-C", str(dest), "describe", "--tags", "--abbrev=0"],
        capture_output=True, text=True,
    )
    latest = result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "no tags"
    print(f"  {dest.name}: latest_tag={latest}")


def main() -> int:
    failures: list[str] = []
    for pkg_id, pkg in PACKAGES.items():
        github_repo = pkg["github_repo"]
        required = pkg.get("required", True)
        dest = ROOT_DIR / github_repo.split("/")[-1]
        if not clone(github_repo, dest, required):
            failures.append(github_repo)
            continue
        fetch_tags(dest)

    if failures:
        print("\nRequired repos failed to clone:")
        for repo in failures:
            print(f"  - {repo}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
