"""
Configuration for the pathsim-docs build system.
"""

from pathlib import Path

# Directory paths
SCRIPT_DIR = Path(__file__).parent.parent
PROJECT_ROOT = SCRIPT_DIR.parent
ROOT_DIR = PROJECT_ROOT.parent  # Parent of pathsim-docs (contains pathsim repos)
STATIC_DIR = PROJECT_ROOT / "static"
GENERATED_DIR = PROJECT_ROOT / "src" / "lib" / "api" / "generated"

# Package configuration
PACKAGES = {
    "pathsim": {
        "repo": ROOT_DIR / "pathsim",
        "source": ROOT_DIR / "pathsim" / "src",
        "notebooks": ROOT_DIR / "pathsim" / "docs" / "source" / "examples",
        "figures": ROOT_DIR / "pathsim" / "docs" / "source" / "examples" / "figures",
        "display_name": "PathSim",
        "griffe_package": "pathsim",
        "github_repo": "pathsim/pathsim",
        "root_modules": [
            "pathsim",
        ],
    },
    "chem": {
        "repo": ROOT_DIR / "pathsim-chem",
        "source": ROOT_DIR / "pathsim-chem" / "src",
        "notebooks": ROOT_DIR / "pathsim-chem" / "docs" / "source" / "examples",
        "figures": ROOT_DIR / "pathsim-chem" / "docs" / "source" / "examples" / "figures",
        "display_name": "PathSim-Chem",
        "griffe_package": "pathsim_chem",
        "github_repo": "pathsim/pathsim-chem",
        "root_modules": [
            "pathsim_chem",
        ],
    },
    "batt": {
        "repo": ROOT_DIR / "pathsim-batt",
        "source": ROOT_DIR / "pathsim-batt" / "src",
        "notebooks": ROOT_DIR / "pathsim-batt" / "docs" / "source" / "examples",
        "figures": ROOT_DIR / "pathsim-batt" / "docs" / "source" / "examples" / "figures",
        "display_name": "PathSim-Batt",
        "griffe_package": "pathsim_batt",
        "github_repo": "pathsim/pathsim-batt",
        "root_modules": [
            "pathsim_batt",
        ],
    },
    "vehicle": {
        "repo": ROOT_DIR / "pathsim-vehicle",
        "source": ROOT_DIR / "pathsim-vehicle" / "src",
        "notebooks": ROOT_DIR / "pathsim-vehicle" / "docs" / "source" / "examples",
        "figures": ROOT_DIR / "pathsim-vehicle" / "docs" / "source" / "examples" / "figures",
        "display_name": "PathSim-Vehicle",
        "griffe_package": "pathsim_vehicle",
        "github_repo": "pathsim/pathsim-vehicle",
        "root_modules": [
            "pathsim_vehicle",
        ],
    },
    "flight": {
        "repo": ROOT_DIR / "pathsim-flight",
        "source": ROOT_DIR / "pathsim-flight" / "src",
        "notebooks": ROOT_DIR / "pathsim-flight" / "docs" / "source" / "examples",
        "figures": ROOT_DIR / "pathsim-flight" / "docs" / "source" / "examples" / "figures",
        "display_name": "PathSim-Flight",
        "griffe_package": "pathsim_flight",
        "github_repo": "pathsim/pathsim-flight",
        "root_modules": [
            "pathsim_flight",
        ],
        "required": False,
    },
    "rf": {
        "repo": ROOT_DIR / "pathsim-rf",
        "source": ROOT_DIR / "pathsim-rf" / "src",
        "notebooks": ROOT_DIR / "pathsim-rf" / "docs" / "source" / "examples",
        "figures": ROOT_DIR / "pathsim-rf" / "docs" / "source" / "examples" / "figures",
        "display_name": "PathSim-RF",
        "griffe_package": "pathsim_rf",
        "github_repo": "pathsim/pathsim-rf",
        "root_modules": [
            "pathsim_rf",
        ],
        "required": False,
    },
}

# Minimum supported versions per package
# Only versions >= this will be extracted
MIN_SUPPORTED_VERSIONS = {
    "pathsim": "0.7",
    "chem": "0.1",
    "batt": "0.1",
    "vehicle": "0.1",
    "flight": "0.1",
    "rf": "0.1",
}

# Patterns to skip during API extraction
SKIP_PATTERNS = ["_constants", "_version", "__pycache__"]

# Notebook category mappings
CATEGORY_MAPPINGS = {
    # Getting Started
    "harmonic_oscillator": ("getting-started", ["ode", "basics"]),
    "pendulum": ("getting-started", ["ode", "adaptive", "physics"]),
    "vanderpol": ("getting-started", ["ode", "nonlinear"]),
    "linear_feedback": ("getting-started", ["ode", "feedback"]),

    # Control Systems
    "pid_controller": ("control", ["pid", "feedback"]),
    "cascade_controller": ("control", ["cascade", "feedback"]),
    "dcmotor_control": ("control", ["motor", "pid"]),
    "kalman_filter": ("control", ["estimation", "filter"]),
    "thermostat": ("control", ["hybrid", "events"]),
    "abs_braking": ("control", ["hybrid", "events", "automotive"]),

    # Mechanics
    "bouncing_ball": ("mechanics", ["events", "hybrid"]),
    "bouncing_pendulum": ("mechanics", ["events", "collision"]),
    "switched_bouncing_ball": ("mechanics", ["events", "hybrid"]),
    "stick_slip": ("mechanics", ["friction", "hybrid"]),
    "elastic_pendulum": ("mechanics", ["ode", "physics"]),
    "billards": ("mechanics", ["events", "collision"]),
    "coupled_oscillators": ("mechanics", ["ode", "physics"]),

    # Electronics
    "diode_circuit": ("electronics", ["nonlinear", "circuit"]),
    "noisy_amplifier": ("electronics", ["noise", "circuit"]),
    "delta_sigma_adc": ("electronics", ["adc", "mixed-signal"]),
    "sar_adc": ("electronics", ["adc", "mixed-signal"]),

    # Signal Processing
    "spectrum_analysis": ("signal-processing", ["fft", "frequency"]),
    "fmcw_radar": ("signal-processing", ["radar", "frequency"]),
    "transfer_function": ("signal-processing", ["frequency", "bode"]),
    "rf_network_oneport": ("signal-processing", ["rf", "network"]),

    # Chemical
    "chemical_reactor": ("chemical", ["cstr", "reaction"]),
    "vapor_pressure_curves": ("chemical", ["thermodynamics", "vle"]),
    "equation_of_state": ("chemical", ["thermodynamics", "eos"]),
    "vle_calculation": ("chemical", ["thermodynamics", "vle"]),
    "cstr_reaction": ("chemical", ["cstr", "reaction", "dynamics"]),
    "heat_exchanger": ("chemical", ["heat-transfer", "dynamics"]),
    "flash_distillation": ("chemical", ["separation", "vle", "distillation"]),

    # Advanced
    "algebraic_loop": ("advanced", ["algebraic", "solver"]),
    "nested_subsystems": ("advanced", ["hierarchy", "subsystem"]),
    "lorenz_attractor": ("advanced", ["chaos", "ode"]),
    "poincare_maps": ("advanced", ["analysis", "chaos"]),

    # RF Engineering
    "rf_amplifier_compression": ("rf-engineering", ["amplifier", "nonlinear", "compression"]),
    "rf_mixer_downconversion": ("rf-engineering", ["mixer", "frequency", "downconversion"]),
    "transmission_line_reflection": ("rf-engineering", ["transmission-line", "propagation"]),
    "superheterodyne_receiver": ("rf-engineering", ["receiver", "system"]),

    # FMU Integration
    "fmu_cosimulation": ("fmu", ["fmu", "cosim"]),
    "fmu_model_exchange_bouncing_ball": ("fmu", ["fmu", "model-exchange"]),
    "fmu_model_exchange_vanderpol": ("fmu", ["fmu", "model-exchange"]),
}

# Non-executable notebooks
NON_EXECUTABLE = {
    "fmu_cosimulation",
    "fmu_model_exchange_bouncing_ball",
    "fmu_model_exchange_vanderpol",
    "rf_network_oneport",
}

# Notebook categories
CATEGORIES = [
    {"id": "getting-started", "title": "Getting Started", "order": 1},
    {"id": "control", "title": "Control Systems", "order": 2},
    {"id": "mechanics", "title": "Mechanics", "order": 3},
    {"id": "electronics", "title": "Electronics", "order": 4},
    {"id": "signal-processing", "title": "Signal Processing", "order": 5},
    {"id": "chemical", "title": "Chemical Engineering", "order": 6},
    {"id": "advanced", "title": "Advanced Topics", "order": 7},
    {"id": "rf-engineering", "title": "RF Engineering", "order": 8},
    {"id": "fmu", "title": "FMU Integration", "order": 9},
]

# Execution settings
MAX_WORKERS = 4  # Parallel notebook execution
NOTEBOOK_TIMEOUT = 300  # 5 minutes per notebook

# ---------------------------------------------------------------------------
# Image / figure optimization
# ---------------------------------------------------------------------------
# Every raster figure that lands in the served static/ tree is re-encoded to
# WebP at build time so the site stays snappy. SVG (and other vector formats)
# are passed through untouched — they are already small and scale crisply.

# Raster extensions that get re-encoded to WebP. Anything not in this set and
# not vector is copied verbatim.
RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}

# Vector formats are never rasterized; copied as-is.
VECTOR_EXTENSIONS = {".svg"}

# WebP quality for lossy sources (photos, JPEGs). 0-100.
WEBP_QUALITY = 82

# Pillow compression effort, 0 (fast) - 6 (best/slowest).
WEBP_METHOD = 6

# Source extensions that should be encoded losslessly (flat-color diagrams,
# screenshots, anything with sharp edges or text where lossy artifacts show).
WEBP_LOSSLESS_EXTENSIONS = {".png", ".gif", ".bmp"}

# ---------------------------------------------------------------------------
# TikZ rendering (docstring `.. tikz::` directive -> SVG at build time)
# ---------------------------------------------------------------------------
# Candidate LaTeX engines, tried in order. tectonic is preferred in CI (single
# self-contained binary, fetches packages on demand); pdflatex/lualatex cover
# local builds (e.g. MiKTeX on Windows).
TIKZ_LATEX_ENGINES = ["tectonic", "lualatex", "pdflatex"]

# Candidate PDF->SVG converters, tried in order. dvisvgm embeds fonts as paths
# (crispest result); pdftocairo/pdf2svg are fallbacks.
TIKZ_PDF_TO_SVG = ["dvisvgm", "pdftocairo", "pdf2svg"]

# Seconds before a single TikZ compile is abandoned.
TIKZ_TIMEOUT = 60
