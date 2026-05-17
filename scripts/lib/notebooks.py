"""
Notebook utilities for copying and metadata extraction.
"""

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .config import CATEGORY_MAPPINGS, CATEGORIES, NON_EXECUTABLE


def copy_notebooks(source_dir: Path, target_dir: Path, docs_root: Path | None = None) -> list[dict]:
    """
    Copy notebooks from source to target directory and extract metadata.

    Args:
        source_dir: Directory containing notebooks
        target_dir: Output directory for this version
        docs_root: Root of docs directory to search for figures (optional)

    Returns list of notebook metadata dictionaries.
    """
    if not source_dir.exists():
        return []

    notebooks_dir = target_dir / "notebooks"
    notebooks_dir.mkdir(parents=True, exist_ok=True)

    notebooks = []
    all_figure_refs = set()

    for nb_path in sorted(source_dir.glob("*.ipynb")):
        try:
            meta = _process_notebook(nb_path, notebooks_dir)
            if meta:
                notebooks.append(meta)
                # Collect figure references from this notebook
                figure_refs = extract_figure_paths(nb_path)
                all_figure_refs.update(figure_refs)
        except Exception as e:
            print(f"    Warning: Failed to process {nb_path.name}: {e}")

    # Copy mplstyle file if it exists (notebooks reference ../pathsim_docs.mplstyle)
    mplstyle_source = source_dir.parent / "pathsim_docs.mplstyle"
    if mplstyle_source.exists():
        shutil.copy2(mplstyle_source, target_dir / "pathsim_docs.mplstyle")

    # Copy referenced figures by searching docs directory
    if all_figure_refs:
        search_root = docs_root or source_dir.parent
        copy_notebook_figures(all_figure_refs, search_root, target_dir)

    return notebooks


def extract_figure_paths(notebook_path: Path) -> set[str]:
    """
    Extract all figure paths referenced in a notebook.

    Looks for image references in markdown and raw cells using:
    - RST syntax: .. image:: path
    - Markdown syntax: ![alt](path)
    - HTML syntax: <img src="path">

    Returns set of figure filenames (just the filename, not full path).
    """
    try:
        with open(notebook_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return set()

    figure_refs = set()

    # Patterns for different image syntaxes
    patterns = [
        re.compile(r'\.\.\s+image::\s*(\S+)'),  # RST: .. image:: path
        re.compile(r'!\[[^\]]*\]\(([^)]+)\)'),  # Markdown: ![alt](path)
        re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE),  # HTML: <img src="path">
    ]

    for cell in notebook.get("cells", []):
        cell_type = cell.get("cell_type")
        if cell_type not in ("markdown", "raw"):
            continue

        source = cell.get("source", [])
        if isinstance(source, list):
            source = "".join(source)

        for pattern in patterns:
            for match in pattern.finditer(source):
                path = match.group(1)
                # Extract just the filename from the path
                # Handle paths like "figures/figures_g/foo.png" or "../figures/bar.png"
                filename = Path(path.replace("\\", "/")).name
                if filename.lower().endswith((".png", ".jpg", ".jpeg", ".svg", ".gif")):
                    figure_refs.add(filename)

    return figure_refs


def copy_notebook_figures(figure_refs: set[str], search_root: Path, target_dir: Path) -> int:
    """
    Search for referenced figures in the docs directory and copy them.

    Args:
        figure_refs: Set of figure filenames to find
        search_root: Root directory to search in
        target_dir: Output directory for this version

    Returns number of figures copied.
    """
    figures_dir = target_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Build index of all image files in search_root
    image_index: dict[str, Path] = {}
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.svg", "*.gif"]:
        for img_path in search_root.rglob(ext):
            # Use lowercase filename as key for case-insensitive matching
            image_index[img_path.name.lower()] = img_path

    copied = 0
    not_found = []

    for ref in figure_refs:
        ref_lower = ref.lower()
        if ref_lower in image_index:
            src_path = image_index[ref_lower]
            # Determine target path - preserve subdirectory structure if in figures_g etc
            rel_parts = src_path.relative_to(search_root).parts
            # Check if it's in a subdirectory of figures
            if "figures" in rel_parts:
                fig_idx = rel_parts.index("figures")
                sub_parts = rel_parts[fig_idx + 1:]
                if len(sub_parts) > 1:
                    # Has subdirectory (e.g., figures_g)
                    subdir = figures_dir / sub_parts[0]
                    subdir.mkdir(parents=True, exist_ok=True)
                    dest_path = subdir / sub_parts[-1]
                else:
                    dest_path = figures_dir / sub_parts[-1] if sub_parts else figures_dir / src_path.name
            else:
                dest_path = figures_dir / src_path.name

            if not dest_path.exists():
                shutil.copy2(src_path, dest_path)
                copied += 1
        else:
            not_found.append(ref)

    if not_found:
        print(f"      Warning: {len(not_found)} figures not found: {not_found[:3]}{'...' if len(not_found) > 3 else ''}")

    return copied


def copy_figures(source_dir: Path, target_dir: Path):
    """
    Copy figures from source to target figures directory.

    DEPRECATED: Use copy_notebook_figures() with extract_figure_paths() instead.
    Kept for backward compatibility.
    """
    if not source_dir.exists():
        return

    figures_dir = target_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Copy all image files
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.svg", "*.gif"]:
        for fig in source_dir.glob(ext):
            shutil.copy2(fig, figures_dir / fig.name)

    # Also copy from subdirectories (like figures_g)
    for subdir in source_dir.iterdir():
        if subdir.is_dir():
            subdir_out = figures_dir / subdir.name
            subdir_out.mkdir(parents=True, exist_ok=True)
            for ext in ["*.png", "*.jpg", "*.jpeg", "*.svg", "*.gif"]:
                for fig in subdir.glob(ext):
                    shutil.copy2(fig, subdir_out / fig.name)


def _process_notebook(nb_path: Path, output_dir: Path) -> dict | None:
    """Process a single notebook: copy and extract metadata."""
    try:
        with open(nb_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"    Warning: Could not parse {nb_path.name}: {e}")
        return None

    stem = nb_path.stem
    slug = _slugify(stem)

    # Extract metadata
    title = _extract_title(notebook)
    description = _extract_description(notebook)
    thumbnail_path = _extract_thumbnail(notebook)

    # Get category and tags from mapping
    category, tags = CATEGORY_MAPPINGS.get(stem, ("advanced", []))

    # Check if executable
    executable = stem not in NON_EXECUTABLE

    # Copy notebook (without outputs - clean copy)
    clean_notebook = _strip_outputs(notebook)
    output_path = output_dir / nb_path.name
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clean_notebook, f, indent=1, ensure_ascii=False)

    # Process thumbnail path - convert to figures-relative path
    thumbnail = None
    if thumbnail_path:
        # Handle relative paths like "../figures/image.png" or "figures/image.png"
        # Extract just the filename or subdirectory/filename
        path_parts = Path(thumbnail_path.replace("\\", "/"))
        # Get the path relative to figures directory
        # Common patterns: ../figures/foo.png, figures/foo.png, ./figures/foo.png
        parts = path_parts.parts
        if "figures" in parts:
            # Find index of 'figures' and take everything after
            fig_idx = parts.index("figures")
            thumbnail = "/".join(parts[fig_idx + 1:])
        else:
            # Just use the filename
            thumbnail = path_parts.name

    result = {
        "slug": slug,
        "file": nb_path.name,
        "title": title,
        "description": description,
        "category": category,
        "tags": tags,
        "executable": executable,
    }

    if thumbnail:
        result["thumbnail"] = thumbnail

    return result


def _strip_outputs(notebook: dict) -> dict:
    """Remove outputs from notebook cells (keep source only)."""
    clean = dict(notebook)
    clean["cells"] = []

    for cell in notebook.get("cells", []):
        clean_cell = dict(cell)
        if cell.get("cell_type") == "code":
            clean_cell["outputs"] = []
            clean_cell["execution_count"] = None
        clean["cells"].append(clean_cell)

    return clean


def _slugify(name: str) -> str:
    """Convert filename to URL-friendly slug."""
    return name.lower().replace("_", "-").replace(" ", "-")


def _extract_title(notebook: dict) -> str:
    """Extract title from first markdown cell (H1 heading)."""
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = cell.get("source", [])
            if isinstance(source, list):
                source = "".join(source)

            match = re.search(r"^#\s+(.+?)(?:\n|$)", source, re.MULTILINE)
            if match:
                return match.group(1).strip()

    return "Untitled"


def _extract_thumbnail(notebook: dict) -> str | None:
    """Extract first image path from markdown cells.

    Looks for images in markdown cells using:
    - Markdown syntax: ![alt](path)
    - HTML syntax: <img src="path">
    - RST syntax: .. image:: path

    Returns the image path (relative to notebook) or None if not found.
    """
    # Pattern for markdown images: ![alt](path)
    md_pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
    # Pattern for HTML images: <img src="path"> or <img src='path'>
    html_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
    # Pattern for RST images: .. image:: path
    rst_pattern = re.compile(r'\.\.\s+image::\s*(\S+)')

    for cell in notebook.get("cells", []):
        cell_type = cell.get("cell_type")
        # Check markdown and raw cells (RST is often in raw cells)
        if cell_type in ("markdown", "raw"):
            source = cell.get("source", [])
            if isinstance(source, list):
                source = "".join(source)

            # Try markdown syntax first
            match = md_pattern.search(source)
            if match:
                return match.group(1)

            # Try HTML syntax
            match = html_pattern.search(source)
            if match:
                return match.group(1)

            # Try RST syntax
            match = rst_pattern.search(source)
            if match:
                return match.group(1)

    return None


def _extract_description(notebook: dict) -> str:
    """Extract description from first paragraph after title.

    Handles both cases:
    - Title and description in same cell (# Title\\n\\nDescription...)
    - Title in one cell, description in next markdown cell
    """
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = cell.get("source", [])
            if isinstance(source, list):
                source = "".join(source)

            # Check if cell starts with a title
            title_match = re.match(r"^#\s+.+", source)
            if title_match:
                # Remove the title line and look for description in same cell
                after_title = source[title_match.end():].strip()
                if after_title:
                    # Description is in same cell as title
                    desc = _clean_description(after_title)
                    if desc:
                        return desc
                # If no description after title in this cell, continue to next cell
                continue

            # This is a markdown cell without a title - could be description
            desc = _clean_description(source)
            if desc:
                return desc

    return "Example notebook"


def _clean_description(text: str) -> str:
    """Clean markdown text and extract first meaningful paragraph."""
    # Remove markdown formatting
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
    text = re.sub(r"`([^`]+)`", r"\1", text)  # inline code: keep content, drop backticks
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*([^*]+)\*", r"\1", text)  # italic
    text = re.sub(r"^\s*#+\s+.+$", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"\$\$[^$]*\$\$", "", text, flags=re.DOTALL)  # display math
    text = re.sub(r"\$[^$]+\$", "", text)  # inline math
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)  # list items
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)  # numbered lists

    # Get first non-empty line that looks like a sentence
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines:
        # Skip lines that look like code, equations, or fragments
        if line.startswith(("import ", "from ", "```", ">>>")):
            continue
        if re.match(r"^[\W\d]+$", line):  # only symbols/numbers
            continue
        if len(line) < 10:  # too short to be meaningful
            continue
        # Found a good line
        if len(line) > 200:
            line = line[:197] + "..."
        return line

    return ""


def generate_version_manifest(
    package_id: str,
    tag: str,
    notebooks: list[dict],
) -> dict[str, Any]:
    """Generate the version-specific manifest."""
    # Sort notebooks by category order, then by title
    category_order = {c["id"]: c["order"] for c in CATEGORIES}
    sorted_notebooks = sorted(
        notebooks,
        key=lambda n: (category_order.get(n["category"], 99), n["title"])
    )

    # Only emit categories that this package actually uses. The full CATEGORIES
    # list was previously dumped into every manifest — typically 8 out of 9
    # categories were empty per package, bloating manifests and confusing the
    # frontend TOC.
    used_category_ids = {n["category"] for n in sorted_notebooks}
    used_categories = [c for c in CATEGORIES if c["id"] in used_category_ids]

    return {
        "package": package_id,
        "tag": tag,
        "notebooks": sorted_notebooks,
        "categories": used_categories,
    }
