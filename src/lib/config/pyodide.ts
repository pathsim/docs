// Pyodide configuration for documentation notebooks

export const PYODIDE_VERSION = '0.26.2';
// Self-hosted Pyodide assets — fetched into static/pyodide/ at build time
// by scripts/fetch-pyodide.py. Same-origin avoids cross-origin module
// resolution quirks (e.g. Firefox failing to derive indexURL from
// import.meta.url) and removes the runtime jsdelivr dependency.
export const PYODIDE_INDEX_URL = '/pyodide/';
export const PYODIDE_MODULE_URL = `${PYODIDE_INDEX_URL}pyodide.mjs`;

// Packages preloaded with Pyodide (available as built-in Pyodide packages)
export const PYODIDE_PRELOAD = ['numpy', 'scipy', 'micropip'] as const;

export interface PackageConfig {
	pip: string;
	required: boolean;
	pre: boolean;
	import: string;
}

// Base packages always installed (utilities, not simulation packages)
export const BASE_PACKAGES: PackageConfig[] = [
	{
		pip: 'matplotlib',
		required: true,
		pre: false,
		import: 'matplotlib'
	}
];

// Timeouts in milliseconds
export const TIMEOUTS = {
	INIT: 120000, // 2 min for loading Pyodide + packages
	EXECUTION: 60000 // 1 min per cell
} as const;

// Progress messages
export const PROGRESS_MESSAGES = {
	LOADING_PYODIDE: 'Loading Python runtime...',
	INSTALLING_DEPS: 'Installing core packages...',
	INSTALLING_PATHSIM: 'Installing pathsim...',
	INSTALLING_MATPLOTLIB: 'Installing matplotlib...',
	READY: 'Python environment ready'
} as const;

// Error messages
export const ERROR_MESSAGES = {
	FAILED_TO_LOAD_PYODIDE: 'Failed to load Pyodide runtime',
	WORKER_NOT_INITIALIZED: 'Pyodide worker not initialized',
	EXECUTION_TIMEOUT: 'Code execution timed out'
} as const;
