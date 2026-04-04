/**
 * Pyodide Web Worker
 * Executes Python code in a separate thread for documentation notebooks
 */

import {
	PYODIDE_CDN_URL,
	PYODIDE_PRELOAD,
	BASE_PACKAGES,
	PROGRESS_MESSAGES,
	ERROR_MESSAGES,
	type PackageConfig
} from '$lib/config/pyodide';
import type { WorkerRequest, WorkerResponse, PackageVersions, PyodidePackageInfo } from './types';

// Pyodide types (loaded dynamically from CDN)
interface PyodideInterface {
	runPythonAsync(code: string): Promise<unknown>;
	loadPackage(packages: readonly string[]): Promise<void>;
	setStdout(options: { batched: (msg: string) => void }): void;
	setStderr(options: { batched: (msg: string) => void }): void;
}

let pyodide: PyodideInterface | null = null;
let isInitialized = false;

// Execution tracking for stdout/stderr routing
let currentExecId: string | null = null;

/**
 * Send a response to the main thread
 */
function send(response: WorkerResponse): void {
	postMessage(response);
}

/**
 * Initialize Pyodide and install packages
 * @param dynamicPackages Simulation packages to install (from package config)
 * @param packageVersions Optional version overrides for packages (e.g., { pathsim: '0.16.4' })
 */
async function initialize(dynamicPackages?: PyodidePackageInfo[], packageVersions?: PackageVersions): Promise<void> {
	if (isInitialized) {
		send({ type: 'ready' });
		return;
	}

	send({ type: 'progress', message: PROGRESS_MESSAGES.LOADING_PYODIDE });

	// Dynamic import of Pyodide from CDN
	const { loadPyodide } = await import(
		/* @vite-ignore */
		PYODIDE_CDN_URL
	);

	pyodide = await loadPyodide();
	if (!pyodide) throw new Error(ERROR_MESSAGES.FAILED_TO_LOAD_PYODIDE);

	// Setup stdout/stderr capture with routing to current execution
	pyodide.setStdout({
		batched: (msg: string) => {
			if (currentExecId) {
				send({ type: 'stdout', id: currentExecId, text: msg });
			}
		}
	});
	pyodide.setStderr({
		batched: (msg: string) => {
			if (currentExecId) {
				send({ type: 'stderr', id: currentExecId, text: msg });
			}
		}
	});

	// Load preloaded packages (numpy, scipy, micropip)
	send({ type: 'progress', message: PROGRESS_MESSAGES.INSTALLING_DEPS });
	await pyodide.loadPackage([...PYODIDE_PRELOAD]);

	// Build package list: dynamic simulation packages first, then base packages
	const allPackages: PackageConfig[] = [
		...(dynamicPackages ?? []).map((p) => ({
			pip: p.pip,
			import: p.import,
			pre: p.pre,
			required: true
		})),
		...BASE_PACKAGES
	];

	// Install packages via micropip
	for (const pkg of allPackages) {
		// Check if a specific version was requested for this package
		const version = packageVersions?.[pkg.pip];
		const versionSuffix = version ? `==${version}` : '';

		const versionDisplay = version ? ` ${version}` : '';
		send({
			type: 'progress',
			message: `Installing ${pkg.pip}${versionDisplay}...`
		});

		try {
			const preFlag = pkg.pre ? ', pre=True' : '';
			await pyodide.runPythonAsync(`
import micropip
await micropip.install('${pkg.pip}${versionSuffix}'${preFlag})
			`);

			// Verify installation
			await pyodide.runPythonAsync(`
import ${pkg.import}
print(f"${pkg.import} {${pkg.import}.__version__} loaded successfully")
			`);
		} catch (error) {
			if (pkg.required) {
				throw new Error(`Failed to install required package ${pkg.pip}${versionSuffix}: ${error}`);
			}
			console.warn(`Optional package ${pkg.pip} failed to install:`, error);
		}
	}

	// Setup matplotlib backend and apply PathSim docs style
	await pyodide.runPythonAsync(`
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import io
import base64

# Apply PathSim documentation style
plt.rcParams.update({
    # Figure
    'figure.figsize': (8, 4),
    'figure.dpi': 150,
    'figure.facecolor': 'none',
    'figure.edgecolor': 'none',
    'savefig.facecolor': 'none',
    'savefig.edgecolor': 'none',
    'savefig.transparent': True,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,

    # Axes
    'axes.facecolor': 'none',
    'axes.edgecolor': '#7F7F7F',
    'axes.linewidth': 1.8,
    'axes.grid': False,
    'axes.axisbelow': True,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'axes.labelcolor': '#7F7F7F',
    'axes.titleweight': 'bold',
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.prop_cycle': plt.cycler('color', ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00']),

    # Grid
    'grid.color': '#7F7F7F',
    'grid.linestyle': '--',
    'grid.linewidth': 0.8,
    'grid.alpha': 0.6,

    # Lines
    'lines.linewidth': 2.0,
    'lines.markersize': 8,
    'lines.markeredgewidth': 1.5,
    'lines.antialiased': True,

    # Patches
    'patch.linewidth': 1.0,
    'patch.facecolor': '#4C72B0',
    'patch.edgecolor': 'none',
    'patch.antialiased': True,

    # Font
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica', 'sans-serif'],
    'font.size': 10,
    'text.color': '#7F7F7F',

    # Legend
    'legend.frameon': False,
    'legend.framealpha': 0.0,
    'legend.fancybox': False,
    'legend.facecolor': 'none',
    'legend.edgecolor': 'none',
    'legend.fontsize': 10,
    'legend.loc': 'best',

    # Ticks
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'xtick.color': '#7F7F7F',
    'ytick.color': '#7F7F7F',
    'xtick.direction': 'out',
    'ytick.direction': 'out',
    'xtick.major.width': 1.8,
    'ytick.major.width': 1.8,
    'xtick.minor.width': 1.2,
    'ytick.minor.width': 1.2,
})

def _capture_plots():
    """Capture all open matplotlib figures as base64 SVGs."""
    plots = []
    for fig_num in plt.get_fignums():
        fig = plt.figure(fig_num)
        buf = io.BytesIO()
        fig.savefig(buf, format='svg', bbox_inches='tight')
        buf.seek(0)
        plots.append(base64.b64encode(buf.read()).decode('utf-8'))
        plt.close(fig)
    return plots
	`);

	// Import numpy as np globally (common convention)
	await pyodide.runPythonAsync(`import numpy as np`);

	// Initialize user namespace for persistent variables between cells
	await pyodide.runPythonAsync(`
_user_namespace = {
    'np': np,
    'plt': plt,
    '__builtins__': __builtins__
}
	`);

	isInitialized = true;
	send({ type: 'progress', message: PROGRESS_MESSAGES.READY });
	send({ type: 'ready' });
}

/**
 * Execute Python code in the user namespace
 */
async function executeCode(id: string, code: string): Promise<void> {
	if (!pyodide) throw new Error(ERROR_MESSAGES.WORKER_NOT_INITIALIZED);

	currentExecId = id;

	try {
		// Execute code in user namespace using exec
		// Encode code as base64 to avoid escaping issues
		const codeBase64 = btoa(unescape(encodeURIComponent(code)));
		await pyodide.runPythonAsync(`
import base64
_code = base64.b64decode('${codeBase64}').decode('utf-8')
exec(_code, _user_namespace)
del _code
		`);

		// Capture any matplotlib plots
		const plotsJson = (await pyodide.runPythonAsync(`
import json
json.dumps(_capture_plots())
		`)) as string;
		const plots: string[] = JSON.parse(plotsJson);

		// Send plots if any were captured
		for (const plotData of plots) {
			send({ type: 'plot', id, data: plotData });
		}

		send({ type: 'result', id });
	} catch (error) {
		const errorMsg = error instanceof Error ? error.message : String(error);

		// Try to get Python traceback
		let traceback: string | undefined;
		try {
			traceback = (await pyodide.runPythonAsync(`
import traceback
traceback.format_exc()
			`)) as string;
		} catch {
			// Ignore traceback extraction errors
		}

		send({ type: 'error', id, error: errorMsg, traceback });
	} finally {
		currentExecId = null;
	}
}

/**
 * Reset user namespace (clear all user-defined variables)
 */
async function resetNamespace(): Promise<void> {
	if (!pyodide) throw new Error(ERROR_MESSAGES.WORKER_NOT_INITIALIZED);

	await pyodide.runPythonAsync(`
# Reset namespace but keep common imports
_user_namespace = {
    'np': np,
    'plt': plt,
    '__builtins__': __builtins__
}
# Clear any open matplotlib figures
plt.close('all')
	`);
}

// Sequential message queue to prevent concurrent execution.
// The async onmessage handler doesn't block the event loop during awaits,
// so without a queue, multiple exec messages could overlap and corrupt
// shared state (currentExecId, Python namespace).
let messageQueue: Promise<void> = Promise.resolve();

self.onmessage = (event: MessageEvent<WorkerRequest>) => {
	messageQueue = messageQueue.then(() => handleMessage(event));
};

async function handleMessage(event: MessageEvent<WorkerRequest>): Promise<void> {
	const { type } = event.data;

	try {
		switch (type) {
			case 'init':
				await initialize(event.data.packages, event.data.packageVersions);
				break;

			case 'exec': {
				const { id, code } = event.data;
				await executeCode(id, code);
				break;
			}

			case 'reset':
				await resetNamespace();
				send({ type: 'result', id: 'reset' });
				break;

			default:
				throw new Error(`Unknown message type: ${type}`);
		}
	} catch (error) {
		send({
			type: 'error',
			error: error instanceof Error ? error.message : String(error)
		});
	}
}
