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
        "root_modules": [
            "pathsim_chem",
        ],
    },
    "vehicle": {
        "repo": ROOT_DIR / "pathsim-vehicle",
        "source": ROOT_DIR / "pathsim-vehicle" / "src",
        "notebooks": ROOT_DIR / "pathsim-vehicle" / "docs" / "source" / "examples",
        "figures": ROOT_DIR / "pathsim-vehicle" / "docs" / "source" / "examples" / "figures",
        "display_name": "PathSim-Vehicle",
        "griffe_package": "pathsim_vehicle",
        "root_modules": [
            "pathsim_vehicle",
        ],
    },
}

# Minimum supported versions per package
# Only versions >= this will be extracted
MIN_SUPPORTED_VERSIONS = {
    "pathsim": "0.7",
    "chem": "0.1",
    "vehicle": "0.1",
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

    # Advanced
    "algebraic_loop": ("advanced", ["algebraic", "solver"]),
    "nested_subsystems": ("advanced", ["hierarchy", "subsystem"]),
    "lorenz_attractor": ("advanced", ["chaos", "ode"]),
    "poincare_maps": ("advanced", ["analysis", "chaos"]),

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
    {"id": "fmu", "title": "FMU Integration", "order": 8},
]

# Execution settings
MAX_WORKERS = 4  # Parallel notebook execution
NOTEBOOK_TIMEOUT = 300  # 5 minutes per notebook
