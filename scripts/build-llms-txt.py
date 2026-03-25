#!/usr/bin/env python3
"""
Generate llms.txt and llms-full.txt for the PathSim documentation site.

These files make the documentation discoverable by AI agents.

Usage:
    python scripts/build-llms-txt.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.config import PACKAGES, STATIC_DIR, CATEGORIES

BASE_URL = "https://docs.pathsim.org"

DESCRIPTION = (
    "PathSim is a Python framework for simulating dynamical systems using "
    "block diagrams. It supports continuous-time, discrete-time, and hybrid "
    "systems with 18+ numerical solvers, hierarchical subsystems, event "
    "handling, and MIMO connections."
)

# Number of example notebooks to include full code for in llms-full.txt
MAX_FULL_EXAMPLES = 3


def load_package_manifest(package_id: str) -> dict | None:
    path = STATIC_DIR / package_id / "manifest.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_version_data(package_id: str, tag: str) -> tuple[dict | None, dict | None]:
    version_dir = STATIC_DIR / package_id / tag
    api_data = None
    manifest = None

    api_path = version_dir / "api.json"
    if api_path.exists():
        with open(api_path, "r", encoding="utf-8") as f:
            api_data = json.load(f)

    manifest_path = version_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    return api_data, manifest


def load_notebook_code(package_id: str, tag: str, filename: str) -> list[str]:
    """Extract code cells from a notebook, filtering out boilerplate."""
    nb_path = STATIC_DIR / package_id / tag / "notebooks" / filename
    if not nb_path.exists():
        return []

    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    code_blocks = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", [])).strip()
        if not src:
            continue
        # Skip pure matplotlib/style boilerplate
        lines = src.split("\n")
        meaningful = [
            l for l in lines
            if not l.strip().startswith("plt.style.use")
            and not l.strip().startswith("plt.show")
            and not l.strip().startswith("plt.figure")
            and not l.strip().startswith("plt.subplot")
            and not l.strip().startswith("plt.tight_layout")
            and not l.strip().startswith("fig,")
            and not l.strip().startswith("fig =")
            and not l.strip().startswith("ax.")
            and not l.strip().startswith("ax,")
            and not l.strip().startswith("axes")
        ]
        cleaned = "\n".join(meaningful).strip()
        if cleaned:
            code_blocks.append(cleaned)

    return code_blocks


def extract_quickstart(api_data: dict) -> str | None:
    """Extract a minimal quickstart from the API data.

    Builds a quickstart showing the basic pattern:
    import -> create blocks -> connect -> simulate.
    """
    if not api_data:
        return None

    modules = api_data.get("modules", {})

    # Collect block class names from blocks modules
    block_names = []
    for mod_name, mod in modules.items():
        if ".blocks." in mod_name:
            for cls in mod.get("classes", []):
                name = cls["name"]
                if not name.startswith("_"):
                    block_names.append(name)

    if not block_names:
        return None

    return None  # We'll use real notebook examples instead


def generate_llms_txt() -> str:
    """Generate the lightweight llms.txt index."""
    lines = []
    lines.append("# PathSim Documentation")
    lines.append("")
    lines.append(f"> {DESCRIPTION}")
    lines.append("")

    # Installation
    lines.append("## Installation")
    lines.append("")
    lines.append("```")
    lines.append("pip install pathsim")
    lines.append("```")
    lines.append("")

    for package_id, pkg_config in PACKAGES.items():
        pkg_manifest = load_package_manifest(package_id)
        if not pkg_manifest:
            continue

        latest = pkg_manifest["latestTag"]
        display_name = pkg_config["display_name"]

        api_data, manifest = load_version_data(package_id, latest)

        lines.append(f"## {display_name} ({latest})")
        lines.append("")

        # API overview
        if api_data:
            api_url = f"{BASE_URL}/{package_id}/{latest}/api"
            lines.append(f"- [{display_name} API Reference]({api_url}): Full API documentation")

            modules = api_data.get("modules", {})
            for module_name, module in modules.items():
                desc = module.get("description", "")
                anchor = module_name.replace(".", "-")
                entry = f"- [{module_name}]({api_url}#{anchor})"
                if desc:
                    entry += f": {desc}"
                lines.append(entry)

                for cls in module.get("classes", []):
                    cls_desc = cls.get("description", "")
                    cls_entry = f"  - [{cls['name']}]({api_url}#{cls['name']})"
                    if cls_desc:
                        cls_entry += f": {cls_desc}"
                    lines.append(cls_entry)

            lines.append("")

        # Examples
        if manifest:
            notebooks = manifest.get("notebooks", [])
            if notebooks:
                lines.append(f"### Examples")
                lines.append("")
                for nb in notebooks:
                    slug = nb.get("slug", "")
                    title = nb.get("title", slug)
                    desc = nb.get("description", "")
                    url = f"{BASE_URL}/{package_id}/{latest}/examples/{slug}"
                    entry = f"- [{title}]({url})"
                    if desc:
                        entry += f": {desc}"
                    lines.append(entry)
                lines.append("")

    # Links
    lines.append("## Links")
    lines.append("")
    lines.append("- [PathSim Homepage](https://pathsim.org): Project homepage")
    lines.append("- [PathView Editor](https://view.pathsim.org): Browser-based visual block diagram editor")
    lines.append("- [PathSim Codegen](https://code.pathsim.org): Generate C99 code from PathSim models")
    lines.append("- [GitHub](https://github.com/pathsim): Source code repositories")
    lines.append("- [PyPI](https://pypi.org/project/pathsim): Python package")
    lines.append("- [JOSS Paper](https://doi.org/10.21105/joss.07484): Published paper")
    lines.append("")

    return "\n".join(lines)


def generate_llms_full_txt() -> str:
    """Generate llms-full.txt with complete API documentation and code examples."""
    lines = []
    lines.append("# PathSim Documentation (Full)")
    lines.append("")
    lines.append(f"> {DESCRIPTION}")
    lines.append("")

    # Installation
    lines.append("## Installation")
    lines.append("")
    lines.append("```bash")
    lines.append("pip install pathsim")
    lines.append("pip install pathsim-chem   # Chemical engineering toolbox")
    lines.append("pip install pathsim-rf     # RF/microwave toolbox")
    lines.append("```")
    lines.append("")

    for package_id, pkg_config in PACKAGES.items():
        pkg_manifest = load_package_manifest(package_id)
        if not pkg_manifest:
            continue

        latest = pkg_manifest["latestTag"]
        display_name = pkg_config["display_name"]

        api_data, manifest = load_version_data(package_id, latest)

        lines.append(f"## {display_name} ({latest})")
        lines.append("")

        # Quickstart from first example notebook
        if manifest:
            notebooks = manifest.get("notebooks", [])
            if notebooks:
                first_nb = notebooks[0]
                code_blocks = load_notebook_code(
                    package_id, latest, first_nb.get("file", "")
                )
                if code_blocks:
                    lines.append("### Quickstart")
                    lines.append("")
                    lines.append(
                        f"From the [{first_nb['title']}]"
                        f"({BASE_URL}/{package_id}/{latest}/examples/{first_nb['slug']}) example:"
                    )
                    lines.append("")
                    lines.append("```python")
                    lines.append("\n\n".join(code_blocks))
                    lines.append("```")
                    lines.append("")

        # Full API content
        if api_data:
            lines.append("### API Reference")
            lines.append("")

            modules = api_data.get("modules", {})
            for module_name, module in modules.items():
                lines.append(f"#### {module_name}")
                lines.append("")

                desc = module.get("description", "")
                if desc:
                    lines.append(desc)
                    lines.append("")

                for cls in module.get("classes", []):
                    cls_name = cls["name"]
                    cls_desc = cls.get("description", "")
                    bases = cls.get("bases", [])

                    base_str = f"({', '.join(bases)})" if bases else ""
                    lines.append(f"##### class {cls_name}{base_str}")
                    lines.append("")

                    if cls_desc:
                        lines.append(cls_desc)
                        lines.append("")

                    # Parameters (constructor args)
                    params = cls.get("parameters", [])
                    if params:
                        lines.append("**Parameters:**")
                        lines.append("")
                        for p in params:
                            p_name = p.get("name", "")
                            p_type = p.get("type", "")
                            p_default = p.get("default", None)
                            p_desc = p.get("description", "")
                            type_str = f" ({p_type})" if p_type else ""
                            default_str = f", default={p_default}" if p_default is not None else ""
                            entry = f"- `{p_name}{type_str}{default_str}`"
                            if p_desc:
                                entry += f" — {p_desc}"
                            lines.append(entry)
                        lines.append("")

                    # Attributes
                    attrs = [
                        a for a in cls.get("attributes", [])
                        if not a.get("name", "").startswith("_")
                    ]
                    if attrs:
                        lines.append("**Attributes:**")
                        lines.append("")
                        for attr in attrs:
                            attr_name = attr.get("name", "")
                            attr_type = attr.get("type", "")
                            attr_desc = attr.get("description", "")
                            type_str = f": {attr_type}" if attr_type else ""
                            entry = f"- `{attr_name}{type_str}`"
                            if attr_desc:
                                entry += f" — {attr_desc}"
                            lines.append(entry)
                        lines.append("")

                    # Methods
                    methods = [
                        m for m in cls.get("methods", [])
                        if not m.get("name", "").startswith("_")
                        or m.get("name") == "__init__"
                    ]
                    if methods:
                        for method in methods:
                            method_name = method.get("name", "")
                            sig = method.get("signature", "()")
                            method_desc = method.get("description", "")
                            lines.append(f"**{cls_name}.{method_name}**`{sig}`")
                            if method_desc:
                                lines.append(f": {method_desc}")
                            # Method parameters
                            m_params = method.get("parameters", [])
                            if m_params:
                                for p in m_params:
                                    p_name = p.get("name", "")
                                    if p_name in ("self", "cls"):
                                        continue
                                    p_desc = p.get("description", "")
                                    p_default = p.get("default", None)
                                    default_str = f", default={p_default}" if p_default is not None else ""
                                    entry = f"  - `{p_name}{default_str}`"
                                    if p_desc:
                                        entry += f" — {p_desc}"
                                    lines.append(entry)
                            lines.append("")

                for func in module.get("functions", []):
                    func_name = func.get("name", "")
                    sig = func.get("signature", "()")
                    func_desc = func.get("description", "")
                    lines.append(f"##### {func_name}`{sig}`")
                    if func_desc:
                        lines.append(func_desc)
                    lines.append("")

        # Example code from notebooks
        if manifest:
            notebooks = manifest.get("notebooks", [])
            if notebooks:
                lines.append("### Examples")
                lines.append("")

                for i, nb in enumerate(notebooks):
                    slug = nb.get("slug", "")
                    title = nb.get("title", slug)
                    desc = nb.get("description", "")
                    tags = nb.get("tags", [])
                    url = f"{BASE_URL}/{package_id}/{latest}/examples/{slug}"

                    lines.append(f"#### [{title}]({url})")
                    if desc:
                        lines.append(desc)
                    if tags:
                        lines.append(f"Tags: {', '.join(tags)}")

                    # Include full code for the first few examples
                    if i < MAX_FULL_EXAMPLES:
                        code_blocks = load_notebook_code(
                            package_id, latest, nb.get("file", "")
                        )
                        if code_blocks:
                            lines.append("")
                            lines.append("```python")
                            lines.append("\n\n".join(code_blocks))
                            lines.append("```")

                    lines.append("")

    # Links
    lines.append("## Links")
    lines.append("")
    lines.append("- [PathSim Homepage](https://pathsim.org): Project homepage")
    lines.append("- [PathView Editor](https://view.pathsim.org): Browser-based visual block diagram editor")
    lines.append("- [PathSim Codegen](https://code.pathsim.org): Generate C99 code from PathSim models")
    lines.append("- [GitHub](https://github.com/pathsim): Source code repositories")
    lines.append("- [PyPI](https://pypi.org/project/pathsim): Python package")
    lines.append("- [JOSS Paper](https://doi.org/10.21105/joss.07484): Published paper")
    lines.append("")

    return "\n".join(lines)


def main():
    output_dir = STATIC_DIR

    llms_txt = generate_llms_txt()
    llms_path = output_dir / "llms.txt"
    with open(llms_path, "w", encoding="utf-8") as f:
        f.write(llms_txt)
    print(f"Generated {llms_path} ({len(llms_txt)} bytes)")

    llms_full_txt = generate_llms_full_txt()
    llms_full_path = output_dir / "llms-full.txt"
    with open(llms_full_path, "w", encoding="utf-8") as f:
        f.write(llms_full_txt)
    print(f"Generated {llms_full_path} ({len(llms_full_txt)} bytes)")


if __name__ == "__main__":
    main()
