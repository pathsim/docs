#!/usr/bin/env python3
"""
PathSim Documentation Builder

Unified build script that extracts API documentation, copies notebooks,
executes them, and generates all manifests.

All content for a version lives in: static/{package}/{tag}/

Usage:
    python scripts/build.py                    # Build missing versions + latest
    python scripts/build.py --all              # Rebuild all versions
    python scripts/build.py --package pathsim  # Single package
    python scripts/build.py --dry-run          # Preview only
    python scripts/build.py --no-execute       # Skip notebook execution
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from lib.config import (
    PACKAGES,
    MIN_SUPPORTED_VERSIONS,
    STATIC_DIR,
)
from lib.git import (
    get_tags,
    get_latest_tag,
    get_minor_zero_tags,
    get_tag_date,
    checkout,
    checkout_main,
    parse_version,
)
from lib.api import extract_api
from lib.notebooks import (
    copy_notebooks,
    copy_figures,
    generate_version_manifest,
)
from lib.executor import execute_notebooks
from lib.roadmap import build_roadmap

# Optional: embeddings for semantic search
try:
    from lib.embeddings import generate_version_embeddings
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False


# ============================================================================
# Index Generation (per-version search and crossref indexes)
# ============================================================================

def generate_version_indexes(
    package_id: str,
    tag: str,
    output_dir: Path,
) -> None:
    """
    Generate search-index.json and crossref-index.json for a specific version.

    These indexes contain:
    - API items (modules, classes, functions, methods)
    - Example items (notebooks with metadata)
    """
    api_path = output_dir / "api.json"
    manifest_path = output_dir / "manifest.json"

    search_items = []
    crossref_items = {}

    # Base paths for this version
    api_base = f"{package_id}/{tag}/api"
    examples_base = f"{package_id}/{tag}/examples"

    # Load API data if exists
    if api_path.exists():
        with open(api_path, "r", encoding="utf-8") as f:
            api_data = json.load(f)

        modules = api_data.get("modules", {})

        for module_name, module in modules.items():
            # Module entry
            search_items.append({
                "type": "module",
                "name": module_name,
                "description": module.get("description", ""),
                "path": f"{api_base}#{module_name.replace('.', '-')}",
                "packageId": package_id,
                "moduleName": module_name
            })

            # Module crossref
            crossref_items[module_name] = {
                "name": module_name,
                "type": "module",
                "packageId": package_id,
                "moduleName": module_name,
                "path": f"{api_base}#{module_name.replace('.', '-')}"
            }

            # Classes
            for cls in module.get("classes", []):
                cls_name = cls["name"]
                cls_path = f"{api_base}#{cls_name}"

                search_items.append({
                    "type": "class",
                    "name": cls_name,
                    "description": cls.get("description", ""),
                    "path": cls_path,
                    "packageId": package_id,
                    "moduleName": module_name
                })

                # Class crossref (multiple keys for flexible lookup)
                class_target = {
                    "name": cls_name,
                    "type": "class",
                    "packageId": package_id,
                    "moduleName": module_name,
                    "path": cls_path
                }
                crossref_items[cls_name] = class_target
                crossref_items[f"{module_name}.{cls_name}"] = class_target
                crossref_items[f"{package_id}.{cls_name}"] = class_target

                # Methods
                for method in cls.get("methods", []):
                    method_name = method["name"]
                    method_path = f"{api_base}#{cls_name}.{method_name}"

                    search_items.append({
                        "type": "method",
                        "name": method_name,
                        "description": method.get("description", ""),
                        "path": method_path,
                        "packageId": package_id,
                        "moduleName": module_name,
                        "parentClass": cls_name
                    })

                    # Method crossref
                    crossref_items[f"{cls_name}.{method_name}"] = {
                        "name": method_name,
                        "type": "method",
                        "packageId": package_id,
                        "moduleName": module_name,
                        "parentClass": cls_name,
                        "path": method_path
                    }

            # Functions
            for func in module.get("functions", []):
                func_name = func["name"]
                func_path = f"{api_base}#{func_name}"

                search_items.append({
                    "type": "function",
                    "name": func_name,
                    "description": func.get("description", ""),
                    "path": func_path,
                    "packageId": package_id,
                    "moduleName": module_name
                })

                # Function crossref
                func_target = {
                    "name": func_name,
                    "type": "function",
                    "packageId": package_id,
                    "moduleName": module_name,
                    "path": func_path
                }
                crossref_items[func_name] = func_target
                crossref_items[f"{module_name}.{func_name}"] = func_target

    # Load notebook manifest if exists
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        for notebook in manifest.get("notebooks", []):
            slug = notebook.get("slug", "")
            search_items.append({
                "type": "example",
                "name": notebook.get("title", ""),
                "description": notebook.get("description", ""),
                "path": f"{examples_base}/{slug}",
                "packageId": package_id,
                "moduleName": notebook.get("category", ""),
                "tags": notebook.get("tags", [])
            })

    # Write indexes
    search_path = output_dir / "search-index.json"
    with open(search_path, "w", encoding="utf-8") as f:
        json.dump(search_items, f, indent=2, ensure_ascii=False)

    crossref_path = output_dir / "crossref-index.json"
    with open(crossref_path, "w", encoding="utf-8") as f:
        json.dump(crossref_items, f, indent=2, ensure_ascii=False)

    print(f"      {len(search_items)} search items, {len(crossref_items)} crossref items")


BUILD_OK_FILE = ".build-ok"


def _is_build_ok(version_dir: Path) -> bool:
    """
    Decide whether a version directory is a successful build that can be skipped.

    Truth sources, in priority order:
    1. A `.build-ok` marker file → build completed successfully on a previous run.
    2. Implicit fallback for legacy builds that predate the marker:
       - manifest.json or api.json exists,
       - if notebooks/ contains any .ipynb files then outputs/ must contain at
         least as many *.json files (allowing fewer when some notebooks are
         marked non-executable — we accept a small slack), and
       - every outputs/*.json reports success: true.

    A build with failed outputs OR a notebooks/ dir without matching outputs/ is
    NOT ok — it gets retried next run.
    """
    if not version_dir.exists():
        return False

    if (version_dir / BUILD_OK_FILE).exists():
        return True

    # Fallback for legacy versions without the marker file
    has_core = (version_dir / "manifest.json").exists() or (version_dir / "api.json").exists()
    if not has_core:
        return False

    notebooks_dir = version_dir / "notebooks"
    outputs_dir = version_dir / "outputs"

    n_notebooks = len(list(notebooks_dir.glob("*.ipynb"))) if notebooks_dir.exists() else 0
    n_outputs = len(list(outputs_dir.glob("*.json"))) if outputs_dir.exists() else 0

    # Notebooks present but nothing executed (e.g. cleaned-up outputs) → rebuild.
    # We don't require an exact match because some notebooks can legitimately be
    # marked non-executable in the manifest and won't produce an output file.
    if n_notebooks > 0 and n_outputs == 0:
        return False

    if outputs_dir.exists():
        for output_file in outputs_dir.glob("*.json"):
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                return False
            if data.get("success") is False:
                return False

    return True


def _write_build_ok(version_dir: Path, notebook_results: dict | None = None) -> None:
    """Write the .build-ok marker capturing how this version was built."""
    summary: dict = {
        "builtAt": datetime.now(timezone.utc).isoformat(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

    if notebook_results is not None:
        total = len(notebook_results)
        failed = sum(1 for r in notebook_results.values() if r.get("success") is False)
        summary["notebooks"] = {"total": total, "failed": failed}

    with open(version_dir / BUILD_OK_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def get_versions_to_build(
    package_id: str,
    tags: list[str],
    rebuild_all: bool = False,
) -> tuple[list[str], list[str]]:
    """
    Determine which versions to build and which to delete.

    Returns (tags_to_build, tags_to_delete).

    Strategy:
    - Always keep vX.Y.0 tags (historical milestones)
    - Keep exactly one "latest" non-.0 tag
    - When a newer tag exists, build it and delete old non-.0 latest
    - A version is considered already built only if `_is_build_ok` returns True
      (presence of `.build-ok` marker, or legacy build with all outputs success:true).
      Versions with failed outputs are retried automatically.
    """
    min_version = MIN_SUPPORTED_VERSIONS.get(package_id, "0.1")
    output_dir = STATIC_DIR / package_id

    # Get historical .0 releases
    historical = set(get_minor_zero_tags(tags, min_version))
    latest_tag = get_latest_tag(tags)

    to_build = []
    to_delete = []

    # Build missing .0 releases
    for tag in historical:
        if rebuild_all or not _is_build_ok(output_dir / tag):
            to_build.append(tag)

    # Handle latest tag
    if latest_tag:
        latest_ok = _is_build_ok(output_dir / latest_tag)

        if rebuild_all or not latest_ok:
            to_build.append(latest_tag)

            # If latest is not a .0 release, check if there's an old non-.0 to delete
            if latest_tag not in historical:
                # Find existing non-.0 versions to clean up
                if output_dir.exists():
                    for existing in output_dir.iterdir():
                        if not existing.is_dir() or not existing.name.startswith("v"):
                            continue
                        if existing.name in historical:
                            continue  # Keep .0 releases
                        if existing.name == latest_tag:
                            continue  # Don't delete what we're building
                        # This is an old non-.0 release, mark for deletion
                        to_delete.append(existing.name)

    # Sort build list by version (highest first)
    to_build.sort(key=parse_version, reverse=True)

    return to_build, to_delete


def build_version(
    package_id: str,
    tag: str,
    dry_run: bool = False,
    execute: bool = True,
) -> bool:
    """Build a single version of a package."""
    pkg_config = PACKAGES[package_id]
    repo_path = pkg_config["repo"]
    output_dir = STATIC_DIR / package_id / tag

    print(f"\n  {tag}")

    if dry_run:
        print(f"    Would build to: {output_dir}")
        return True

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Checkout the tag
    if not checkout(repo_path, tag):
        print(f"    Failed to checkout {tag}")
        return False

    try:
        # 1. Extract API
        print(f"    Extracting API...")
        api_data = extract_api(
            package_id,
            pkg_config["source"],
            pkg_config["root_modules"],
        )

        if api_data["modules"]:
            api_path = output_dir / "api.json"
            with open(api_path, "w", encoding="utf-8") as f:
                json.dump(api_data, f, indent=2, ensure_ascii=False)
            print(f"      {len(api_data['modules'])} modules")
        else:
            print(f"      No modules found")

        # 2. Copy notebooks and referenced figures
        print(f"    Copying notebooks...")
        notebooks_source = pkg_config.get("notebooks")
        notebooks = []

        if notebooks_source and notebooks_source.exists():
            # Use docs/source as root for figure search (covers figures anywhere in docs)
            docs_root = repo_path / "docs" / "source"
            notebooks = copy_notebooks(notebooks_source, output_dir, docs_root)
            print(f"      {len(notebooks)} notebooks")
        else:
            print(f"      No notebooks found")

        # 3. Execute notebooks
        notebook_results: dict = {}
        if execute and notebooks:
            print(f"    Executing notebooks...")
            notebook_results = execute_notebooks(output_dir, notebooks, parallel=True)

        # 4. Generate version manifest
        print(f"    Generating manifest...")
        manifest = generate_version_manifest(package_id, tag, notebooks)
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # 5. Generate version indexes (search + crossref)
        print(f"    Generating indexes...")
        generate_version_indexes(package_id, tag, output_dir)

        # 6. Generate embeddings for semantic search (optional)
        if HAS_EMBEDDINGS:
            print(f"    Generating embeddings...")
            try:
                generated = generate_version_embeddings(output_dir, force=True)
                if not generated:
                    print(f"      Skipped (no search items)")
            except Exception as e:
                print(f"      Warning: {e}")

        # 7. Write .build-ok marker — only on a fully-clean run.
        # Partial failures (some notebook outputs success: false) leave the
        # marker absent so the next CI run picks the version up automatically.
        failed = sum(1 for r in notebook_results.values() if r.get("success") is False)
        if failed == 0:
            _write_build_ok(output_dir, notebook_results)
            print(f"    Done (build-ok written)")
        else:
            print(f"    Done with {failed} notebook failure(s) — marker withheld, will retry next run")
        return True

    except Exception as e:
        print(f"    Error: {e}")
        return False


def generate_package_manifest(package_id: str, dry_run: bool = False):
    """Generate the package-level manifest with all versions."""
    pkg_config = PACKAGES[package_id]
    repo_path = pkg_config["repo"]
    output_dir = STATIC_DIR / package_id

    # Scan for version directories
    version_tags = []

    for version_dir in output_dir.iterdir():
        if not version_dir.is_dir():
            continue
        if not version_dir.name.startswith("v"):
            continue
        version_tags.append(version_dir.name)

    if not version_tags:
        print(f"  No versions found for {package_id}")
        return

    # Sort by semantic version (highest first)
    version_tags.sort(key=parse_version, reverse=True)
    latest_tag = version_tags[0]

    # Build versions list with release dates and examples availability
    versions = []
    for tag in version_tags:
        released = get_tag_date(repo_path, tag)
        # Check if this version has examples
        version_manifest_path = output_dir / tag / "manifest.json"
        has_examples = False
        if version_manifest_path.exists():
            try:
                with open(version_manifest_path, "r", encoding="utf-8") as f:
                    version_manifest = json.load(f)
                    has_examples = len(version_manifest.get("notebooks", [])) > 0
            except Exception:
                pass
        versions.append({
            "tag": tag,
            "released": released,
            "hasExamples": has_examples,
        })

    # Check if roadmap exists
    roadmap_path = output_dir / "roadmap.json"
    has_roadmap = False
    if roadmap_path.exists():
        try:
            with open(roadmap_path, "r", encoding="utf-8") as f:
                roadmap_data = json.load(f)
                has_roadmap = len(roadmap_data.get("issues", [])) > 0
        except Exception:
            pass

    manifest = {
        "package": package_id,
        "latestTag": latest_tag,
        "versions": versions,
        "hasRoadmap": has_roadmap,
    }

    if dry_run:
        print(f"  Would write package manifest: {output_dir / 'manifest.json'}")
        print(f"    Latest: {latest_tag}, {len(versions)} versions")
    else:
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"  Package manifest: {latest_tag}, {len(versions)} versions")


def build_package(
    package_id: str,
    rebuild_all: bool = False,
    dry_run: bool = False,
    execute: bool = True,
) -> int:
    """Build all versions for a package."""
    pkg_config = PACKAGES.get(package_id)
    if not pkg_config:
        print(f"Unknown package: {package_id}")
        return 0

    repo_path = pkg_config["repo"]
    if not repo_path.exists():
        print(f"Repository not found: {repo_path}")
        return 0

    print(f"\n{'=' * 50}")
    print(f"Building {pkg_config['display_name']}")
    print(f"{'=' * 50}")

    # Get all tags
    tags = get_tags(repo_path)
    if not tags:
        print(f"No version tags found")
        return 0

    print(f"Found {len(tags)} tags")

    # Determine which versions to build/delete
    to_build, to_delete = get_versions_to_build(package_id, tags, rebuild_all)

    if not to_build and not to_delete:
        print(f"All versions up to date (use --all to rebuild)")
        generate_package_manifest(package_id, dry_run)
        return 0

    # Delete old non-.0 versions being replaced
    if to_delete:
        print(f"Cleaning up {len(to_delete)} old version(s):")
        for tag in to_delete:
            print(f"  - {tag}")
            if not dry_run:
                version_dir = STATIC_DIR / package_id / tag
                if version_dir.exists():
                    shutil.rmtree(version_dir)

    if to_build:
        print(f"Building {len(to_build)} version(s):")
        for tag in to_build:
            print(f"  - {tag}")

    # Build each version
    built = 0
    for tag in to_build:
        if build_version(package_id, tag, dry_run, execute):
            built += 1

    # Return to main branch
    if not dry_run:
        checkout_main(repo_path)

    # Fetch roadmap issues from GitHub
    print(f"\n  Fetching roadmap...")
    build_roadmap(package_id, dry_run)

    # Generate package manifest
    if not dry_run:
        generate_package_manifest(package_id, dry_run)

    return built


def main():
    parser = argparse.ArgumentParser(
        description="Build PathSim documentation (API + notebooks)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/build.py                    # Build missing + latest
  python scripts/build.py --all              # Rebuild everything
  python scripts/build.py -p pathsim         # Single package
  python scripts/build.py --dry-run          # Preview only
  python scripts/build.py --no-execute       # Skip notebook execution
        """
    )
    parser.add_argument(
        "--package", "-p",
        choices=list(PACKAGES.keys()),
        help="Build single package (default: all)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        dest="rebuild_all",
        help="Rebuild all versions (ignore cache)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview without building"
    )
    parser.add_argument(
        "--no-execute",
        action="store_true",
        help="Skip notebook execution"
    )
    args = parser.parse_args()

    print("PathSim Documentation Builder")
    print("=" * 50)
    print(f"Mode: {'REBUILD ALL' if args.rebuild_all else 'SMART (missing + latest)'}")
    print(f"Execute notebooks: {'NO' if args.no_execute else 'YES'}")
    print(f"Embeddings: {'YES' if HAS_EMBEDDINGS else 'NO (install sentence-transformers)'}")
    if args.dry_run:
        print("DRY RUN - no files will be written")

    # Determine packages to build
    packages = [args.package] if args.package else list(PACKAGES.keys())

    total_built = 0
    for pkg_id in packages:
        built = build_package(
            pkg_id,
            rebuild_all=args.rebuild_all,
            dry_run=args.dry_run,
            execute=not args.no_execute,
        )
        total_built += built

    print(f"\n{'=' * 50}")
    print(f"Summary: Built {total_built} version(s)")
    print(f"Output: {STATIC_DIR}")


if __name__ == "__main__":
    main()
