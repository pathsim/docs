#!/usr/bin/env python3
"""Download and extract the Pyodide release matching PYODIDE_VERSION
defined in src/lib/config/pyodide.ts.

The full Pyodide tarball ships every package in the distribution (>1 GB),
which exceeds GitHub Pages' per-file limit. We only keep the runtime
core plus the packages our notebooks actually load (numpy, scipy,
micropip, matplotlib + transitive deps as listed in pyodide-lock.json).

Idempotent: skips download when static/pyodide/.version already records
the matching version.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "src" / "lib" / "config" / "pyodide.ts"
TARGET_DIR = PROJECT_ROOT / "static" / "pyodide"
VERSION_MARKER = TARGET_DIR / ".version"

# Packages we explicitly load — runtime deps are resolved via pyodide-lock.json
ROOT_PACKAGES = ("numpy", "scipy", "micropip", "matplotlib")
LOCKFILE_NAME = "pyodide-lock.json"


def read_version() -> str:
    content = CONFIG_FILE.read_text()
    match = re.search(r"PYODIDE_VERSION\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not match:
        raise RuntimeError(f"PYODIDE_VERSION not found in {CONFIG_FILE}")
    return match.group(1)


def already_installed(version: str) -> bool:
    if not VERSION_MARKER.exists():
        return False
    return VERSION_MARKER.read_text().strip() == version


def resolve_packages(tar: tarfile.TarFile) -> tuple[set[str], set[str]]:
    """Read pyodide-lock.json and return (required_files, all_package_files).

    required_files: filenames needed for ROOT_PACKAGES + transitive depends.
    all_package_files: filenames of every package the lockfile knows about
    (used to drop non-required ones during extraction).
    """
    member = tar.getmember(f"pyodide/{LOCKFILE_NAME}")
    f = tar.extractfile(member)
    if f is None:
        raise RuntimeError(f"Could not extract {LOCKFILE_NAME}")
    lock = json.load(f)
    packages = lock["packages"]

    visited: set[str] = set()
    queue = list(ROOT_PACKAGES)
    while queue:
        name = queue.pop()
        if name in visited:
            continue
        visited.add(name)
        if name not in packages:
            print(f"  Warning: dependency '{name}' not found in lockfile")
            continue
        queue.extend(packages[name].get("depends", []))

    required = {packages[name]["file_name"] for name in visited if name in packages}
    all_files = {pkg["file_name"] for pkg in packages.values()}
    print(f"  Resolved {len(visited)} packages → {len(required)} files kept, "
          f"{len(all_files) - len(required)} dropped")
    return required, all_files


def make_filter(required_files: set[str], all_package_files: set[str]):
    def keep(member: tarfile.TarInfo, path: str):
        base = Path(member.name).name
        if base.endswith("-tests.tar"):
            return None
        # Drop non-required package artifacts; .whl.metadata follows its .whl.
        owner = base.removesuffix(".metadata") if base.endswith(".metadata") else base
        if owner in all_package_files and owner not in required_files:
            return None
        return tarfile.data_filter(member, path)

    return keep


def download_and_extract(version: str) -> None:
    url = (
        f"https://github.com/pyodide/pyodide/releases/download/"
        f"{version}/pyodide-{version}.tar.bz2"
    )
    print(f"Downloading {url} ...")

    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)
    TARGET_DIR.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".tar.bz2", delete=False) as tmp:
        tarball = Path(tmp.name)
    subprocess.run(["curl", "-fL", "-o", str(tarball), url], check=True)

    try:
        with tarfile.open(tarball, "r:bz2") as tar:
            print("Resolving package dependencies from lockfile ...")
            required, all_pkg_files = resolve_packages(tar)

            print(f"Extracting to {TARGET_DIR} ...")
            with tempfile.TemporaryDirectory() as extract_dir:
                tar.extractall(extract_dir, filter=make_filter(required, all_pkg_files))
                inner = Path(extract_dir) / "pyodide"
                if not inner.is_dir():
                    raise RuntimeError(
                        f"Expected 'pyodide/' subdirectory in tarball, got: "
                        f"{[p.name for p in Path(extract_dir).iterdir()]}"
                    )
                shutil.move(str(inner), str(TARGET_DIR))
    finally:
        tarball.unlink(missing_ok=True)

    VERSION_MARKER.write_text(version + "\n")
    size_mb = sum(f.stat().st_size for f in TARGET_DIR.rglob("*") if f.is_file()) / 1024 / 1024
    print(f"Pyodide {version} installed at {TARGET_DIR} ({size_mb:.1f} MiB)")


def main() -> int:
    version = read_version()
    if already_installed(version):
        print(f"Pyodide {version} already present at {TARGET_DIR}, skipping")
        return 0
    download_and_extract(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
