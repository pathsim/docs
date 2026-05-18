"""
Notebook execution utilities.

Executes notebooks and captures outputs (stdout, stderr, figures) separately.
Figures are saved as SVG for better quality and smaller file sizes.
"""

import base64
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import MAX_WORKERS, NOTEBOOK_TIMEOUT


# Setup code to configure matplotlib for SVG output
# This is prepended to notebooks before execution.
#
# Do NOT call matplotlib.use('Agg') here: that activates the bare Agg backend,
# which is non-interactive and bypasses IPython's inline display hooks. plt.show()
# becomes a no-op and nbconvert never sees any image, so cell outputs end up with
# stdout/stderr but figures: []. We need the matplotlib_inline backend (Agg under
# the hood, plus _repr_*_ hooks that emit display_data) — activate it via the
# %matplotlib inline magic before setting figure_formats to SVG.
MATPLOTLIB_SVG_SETUP = '''
from IPython import get_ipython
ipython = get_ipython()
if ipython is not None:
    ipython.run_line_magic('matplotlib', 'inline')
    ipython.run_line_magic('config', "InlineBackend.figure_formats = ['svg']")

import matplotlib.pyplot as plt
plt.rcParams['figure.facecolor'] = 'none'
plt.rcParams['savefig.facecolor'] = 'none'
plt.rcParams['savefig.transparent'] = True
'''


def execute_notebooks(
    version_dir: Path,
    notebooks: list[dict],
    parallel: bool = True,
) -> dict[str, dict]:
    """
    Execute all notebooks and save outputs/figures.

    Args:
        version_dir: The version directory (e.g., static/pathsim/v0.16.4/)
        notebooks: List of notebook metadata dicts
        parallel: Whether to execute in parallel

    Returns:
        Dict mapping notebook name to execution result
    """
    notebooks_dir = version_dir / "notebooks"
    outputs_dir = version_dir / "outputs"
    figures_dir = version_dir / "figures"

    outputs_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Filter to executable notebooks only
    executable = [nb for nb in notebooks if nb.get("executable", True)]

    if not executable:
        return {}

    results = {}

    if parallel and len(executable) > 1:
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    _execute_single_notebook,
                    notebooks_dir / nb["file"],
                    outputs_dir,
                    figures_dir,
                ): nb
                for nb in executable
            }

            for future in as_completed(futures):
                nb = futures[future]
                name = Path(nb["file"]).stem
                try:
                    result = future.result()
                    status = "OK" if result.get("success") else "FAILED"
                    print(f"      {status}: {nb['file']}")
                    results[name] = result
                except Exception as e:
                    print(f"      ERROR: {nb['file']}: {e}")
                    results[name] = {"success": False, "error": str(e), "cells": {}}
    else:
        for nb in executable:
            name = Path(nb["file"]).stem
            try:
                result = _execute_single_notebook(
                    notebooks_dir / nb["file"],
                    outputs_dir,
                    figures_dir,
                )
                status = "OK" if result.get("success") else "FAILED"
                print(f"      {status}: {nb['file']}")
                results[name] = result
            except Exception as e:
                print(f"      ERROR: {nb['file']}: {e}")
                results[name] = {"success": False, "error": str(e), "cells": {}}

    return results


def _execute_single_notebook(
    notebook_path: Path,
    outputs_dir: Path,
    figures_dir: Path,
) -> dict[str, Any]:
    """
    Execute a single notebook and capture outputs.

    Returns dict with execution results.
    """
    name = notebook_path.stem
    start_time = time.time()

    try:
        with open(notebook_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"Failed to read notebook: {e}", "cells": {}}

    # Inject matplotlib SVG setup as first code cell
    notebook_with_setup = _inject_svg_setup(notebook)

    # Write temporary notebook with setup
    temp_notebook_path = notebook_path.with_suffix(".temp.ipynb")
    try:
        with open(temp_notebook_path, "w", encoding="utf-8") as f:
            json.dump(notebook_with_setup, f, ensure_ascii=False)
    except Exception as e:
        return {"success": False, "error": f"Failed to write temp notebook: {e}", "cells": {}}

    # Execute using nbconvert (simpler than manual kernel management)
    result = _execute_with_nbconvert(temp_notebook_path)

    # Clean up temp notebook
    try:
        temp_notebook_path.unlink()
    except Exception:
        pass

    if not result["success"]:
        # Save partial results
        output_data = {
            "cells": {},
            "executedAt": datetime.now(timezone.utc).isoformat(),
            "duration": int((time.time() - start_time) * 1000),
            "success": False,
            "error": result.get("error", "Unknown error"),
        }
        _save_output(outputs_dir / f"{name}.json", output_data)
        return output_data

    # Parse the executed notebook and extract outputs
    try:
        with open(result["output_path"], "r", encoding="utf-8") as f:
            executed_nb = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"Failed to read executed notebook: {e}", "cells": {}}

    # Extract outputs from each cell
    # Skip the first code cell (injected setup) when mapping indices
    cells_output = {}
    figure_count = 0
    setup_cell_skipped = False

    for i, cell in enumerate(executed_nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue

        # Skip the injected setup cell (first code cell)
        if not setup_cell_skipped:
            setup_cell_skipped = True
            continue

        # Adjust index to match original notebook (subtract 1 for skipped setup cell)
        original_index = i - 1

        cell_output = {
            "stdout": None,
            "stderr": None,
            "figures": [],
        }

        for output in cell.get("outputs", []):
            output_type = output.get("output_type")

            if output_type == "stream":
                stream_name = output.get("name", "stdout")
                text = "".join(output.get("text", []))
                if stream_name == "stderr":
                    cell_output["stderr"] = (cell_output["stderr"] or "") + text
                else:
                    cell_output["stdout"] = (cell_output["stdout"] or "") + text

            elif output_type in ("display_data", "execute_result"):
                data = output.get("data", {})

                # Extract images - prefer SVG, fall back to PNG/JPEG
                for mime_type in ["image/svg+xml", "image/png", "image/jpeg"]:
                    if mime_type in data:
                        ext = {
                            "image/svg+xml": "svg",
                            "image/png": "png",
                            "image/jpeg": "jpg",
                        }[mime_type]

                        figure_name = f"{name}_{figure_count}.{ext}"
                        figure_path = figures_dir / figure_name

                        # Decode and save
                        img_data = data[mime_type]
                        if mime_type == "image/svg+xml":
                            if isinstance(img_data, list):
                                img_data = "".join(img_data)
                            figure_path.write_text(img_data, encoding="utf-8")
                        else:
                            if isinstance(img_data, list):
                                img_data = "".join(img_data)
                            figure_path.write_bytes(base64.b64decode(img_data))

                        cell_output["figures"].append(figure_name)
                        figure_count += 1
                        break  # Only save first image format

        # Only include cell if it has output
        if cell_output["stdout"] or cell_output["stderr"] or cell_output["figures"]:
            cells_output[str(original_index)] = cell_output

    # Clean up temporary executed notebook
    if result.get("output_path"):
        try:
            result["output_path"].unlink()
        except Exception:
            pass

    duration = int((time.time() - start_time) * 1000)

    output_data = {
        "cells": cells_output,
        "executedAt": datetime.now(timezone.utc).isoformat(),
        "duration": duration,
        "success": True,
    }

    _save_output(outputs_dir / f"{name}.json", output_data)

    return output_data


def _execute_with_nbconvert(notebook_path: Path) -> dict[str, Any]:
    """Execute notebook using nbconvert."""
    output_path = notebook_path.with_suffix(".executed.ipynb")

    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "nbconvert",
                "--to", "notebook",
                "--execute",
                "--output", str(output_path.name),
                "--ExecutePreprocessor.timeout=" + str(NOTEBOOK_TIMEOUT),
                # Kernel start can be slow on first run after a fresh pip install
                # because Python warm-loads the full simulation stack (PyBaMM,
                # CasADi, torch via sentence-transformers, …). Default 60s wasn't
                # enough on cold CI machines.
                "--ExecutePreprocessor.startup_timeout=180",
                "--ExecutePreprocessor.kernel_name=python3",
                str(notebook_path),
            ],
            cwd=notebook_path.parent,
            capture_output=True,
            text=True,
            timeout=NOTEBOOK_TIMEOUT + 60,
        )

        if result.returncode == 0:
            return {"success": True, "output_path": output_path}
        else:
            # Keep the tail of stderr — usually the traceback ending with the
            # actual exception. 200 chars was too aggressive and obscured the
            # diagnosis of real bugs (e.g. injected-setup-cell syntax errors).
            stderr = (result.stderr or "").strip()
            error = stderr[-2000:] if stderr else "Unknown error"
            return {"success": False, "error": error}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)[:2000]}


def _save_output(path: Path, data: dict):
    """Save output data as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _inject_svg_setup(notebook: dict) -> dict:
    """
    Inject matplotlib SVG setup code as the first code cell.

    This ensures all plots are generated as SVG regardless of
    what the notebook's original settings might be.
    """
    # nbformat allows source as either a single string or a list of strings;
    # when using a list, each element MUST keep its trailing newline, otherwise
    # the kernel reassembles the lines into one undelimited blob that fails to
    # parse (e.g. "import matplotlibmatplotlib.use('Agg')...").
    # A plain multi-line string sidesteps the gotcha entirely.
    setup_cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"tags": ["setup", "hide"]},
        "outputs": [],
        "source": MATPLOTLIB_SVG_SETUP.strip() + "\n",
    }

    # Create a copy with setup cell prepended
    result = dict(notebook)
    result["cells"] = [setup_cell] + list(notebook.get("cells", []))

    return result
