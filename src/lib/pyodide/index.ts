/**
 * Pyodide Bridge
 * Main-thread interface for executing Python code in documentation notebooks
 */

import { TIMEOUTS, ERROR_MESSAGES } from '$lib/config/pyodide';
import { pyodideState, updateState, setError, setReady } from '$lib/stores/pyodideStore';
import type { WorkerRequest, WorkerResponse, ExecutionResult, PackageVersions, PyodidePackageInfo } from './types';

let worker: Worker | null = null;
let initPromise: Promise<void> | null = null;
let initializedVersions: PackageVersions | null = null;
let initializedPackages: PyodidePackageInfo[] | null = null;

// Streaming callbacks for real-time output
export interface StreamCallbacks {
	onStdout?: (text: string) => void;
	onStderr?: (text: string) => void;
	onPlot?: (data: string) => void;
}

// Pending execution promises keyed by execution ID
const pendingExecutions = new Map<
	string,
	{
		resolve: (result: ExecutionResult) => void;
		reject: (error: Error) => void;
		stdout: string[];
		stderr: string[];
		plots: string[];
		startTime: number;
		callbacks?: StreamCallbacks;
	}
>();

// Progress callback for initialization
let progressCallback: ((msg: string) => void) | null = null;

/**
 * Generate unique execution ID
 */
function generateId(): string {
	return `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Handle messages from the worker
 */
function handleWorkerMessage(event: MessageEvent<WorkerResponse>): void {
	const response = event.data;

	switch (response.type) {
		case 'ready':
			setReady();
			break;

		case 'progress':
			updateState({ progress: response.message });
			if (progressCallback) {
				progressCallback(response.message);
			}
			break;

		case 'stdout': {
			const pending = pendingExecutions.get(response.id);
			if (pending) {
				pending.stdout.push(response.text);
				pending.callbacks?.onStdout?.(response.text);
			}
			break;
		}

		case 'stderr': {
			const pending = pendingExecutions.get(response.id);
			if (pending) {
				pending.stderr.push(response.text);
				pending.callbacks?.onStderr?.(response.text);
			}
			break;
		}

		case 'plot': {
			const pending = pendingExecutions.get(response.id);
			if (pending) {
				pending.plots.push(response.data);
				pending.callbacks?.onPlot?.(response.data);
			}
			break;
		}

		case 'result': {
			const pending = pendingExecutions.get(response.id);
			if (pending) {
				pendingExecutions.delete(response.id);
				const duration = Date.now() - pending.startTime;
				pending.resolve({
					stdout: pending.stdout.join('\n'),
					stderr: pending.stderr.join('\n'),
					plots: pending.plots,
					duration
				});
			}
			break;
		}

		case 'error': {
			if (response.id) {
				const pending = pendingExecutions.get(response.id);
				if (pending) {
					pendingExecutions.delete(response.id);
					const duration = Date.now() - pending.startTime;
					pending.resolve({
						stdout: pending.stdout.join('\n'),
						stderr: pending.stderr.join('\n'),
						plots: pending.plots,
						error: {
							message: response.error,
							traceback: response.traceback
						},
						duration
					});
				}
			} else {
				// Global error (e.g., initialization failure)
				setError(response.error);
			}
			break;
		}
	}
}

/**
 * Send a message to the worker
 */
function send(request: WorkerRequest): void {
	if (!worker) {
		throw new Error(ERROR_MESSAGES.WORKER_NOT_INITIALIZED);
	}
	worker.postMessage(request);
}

/**
 * Check if packages or versions have changed and reinitialization is needed
 */
function needsReinitialization(newPackages?: PyodidePackageInfo[], newVersions?: PackageVersions): boolean {
	// No arguments = just checking if initialized, don't force reinit
	if (!newPackages && !newVersions) return false;

	// Check if package list changed
	if (newPackages) {
		if (!initializedPackages) return true;
		const oldPips = new Set(initializedPackages.map((p) => p.pip));
		const newPips = new Set(newPackages.map((p) => p.pip));
		if (oldPips.size !== newPips.size) return true;
		for (const pip of newPips) {
			if (!oldPips.has(pip)) return true;
		}
	}

	// Check if any version has changed
	if (newVersions) {
		if (!initializedVersions) return true;
		for (const [pkg, version] of Object.entries(newVersions)) {
			if (initializedVersions[pkg] !== version) {
				return true;
			}
		}
	}

	return false;
}

/**
 * Initialize Pyodide
 * Returns a promise that resolves when Pyodide is ready
 * @param packages Simulation packages to install (from package config)
 * @param packageVersions Optional package versions to install (e.g., { pathsim: '0.16.4' })
 */
export async function initPyodide(packages?: PyodidePackageInfo[], packageVersions?: PackageVersions): Promise<void> {
	// Check if we need to reinitialize due to package or version change
	if (needsReinitialization(packages, packageVersions)) {
		terminate();
	}

	// Return existing promise if already initializing
	if (initPromise) {
		return initPromise;
	}

	// Already initialized with same versions
	if (worker) {
		return;
	}

	initPromise = new Promise<void>((resolve, reject) => {
		let settled = false;

		// Create worker
		worker = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' });
		worker.onmessage = handleWorkerMessage;
		worker.onerror = (error) => {
			setError(error.message);
			if (!settled) { settled = true; reject(new Error(error.message)); }
		};

		// Wait for ready message
		const originalHandler = handleWorkerMessage;
		worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
			originalHandler(event);
			if (event.data.type === 'ready') {
				worker!.onmessage = originalHandler;
				initializedPackages = packages ?? null;
				initializedVersions = packageVersions ?? null;
				if (!settled) { settled = true; resolve(); }
			} else if (event.data.type === 'error' && !event.data.id) {
				worker!.onmessage = originalHandler;
				if (!settled) { settled = true; reject(new Error(event.data.error)); }
			}
		};

		// Update state and send init message with packages and versions
		updateState({ status: 'loading', progress: 'Starting...', error: null });
		send({ type: 'init', packages, packageVersions });

		// Set timeout
		setTimeout(() => {
			if (!settled) {
				settled = true;
				const error = ERROR_MESSAGES.EXECUTION_TIMEOUT;
				setError(error);
				reject(new Error(error));
			}
		}, TIMEOUTS.INIT);
	});

	return initPromise;
}

/**
 * Execute Python code
 * Returns stdout, stderr, plots, and any error
 * Optionally accepts callbacks for streaming output
 */
export async function execute(
	code: string,
	callbacks?: StreamCallbacks
): Promise<ExecutionResult> {
	// Ensure initialized
	await initPyodide();

	const id = generateId();

	return new Promise<ExecutionResult>((resolve, reject) => {
		// Store pending execution with callbacks
		pendingExecutions.set(id, {
			resolve,
			reject,
			stdout: [],
			stderr: [],
			plots: [],
			startTime: Date.now(),
			callbacks
		});

		// Set timeout
		const timeoutId = setTimeout(() => {
			if (pendingExecutions.has(id)) {
				pendingExecutions.delete(id);
				resolve({
					stdout: '',
					stderr: '',
					plots: [],
					error: {
						message: ERROR_MESSAGES.EXECUTION_TIMEOUT
					},
					duration: TIMEOUTS.EXECUTION
				});
			}
		}, TIMEOUTS.EXECUTION);

		// Clear timeout when execution completes
		const pending = pendingExecutions.get(id)!;
		const originalResolve = pending.resolve;
		pending.resolve = (result) => {
			clearTimeout(timeoutId);
			originalResolve(result);
		};

		// Send execution request
		send({ type: 'exec', id, code });
	});
}

/**
 * Reset the Python namespace
 * Clears all user-defined variables but keeps common imports (np, plt)
 * Only sends reset if the worker is alive and initialized
 */
export function reset(): void {
	if (!worker || !initPromise) return;
	try {
		send({ type: 'reset' });
	} catch {
		// Worker may have been terminated between our check and the send
	}
}

/**
 * Set callback for progress updates during initialization
 */
export function onProgress(callback: (msg: string) => void): void {
	progressCallback = callback;
}

/**
 * Terminate the worker
 * Use this to clean up resources when the component unmounts
 */
export function terminate(): void {
	if (worker) {
		worker.terminate();
		worker = null;
	}
	initPromise = null;
	initializedPackages = null;
	initializedVersions = null;

	// Resolve all pending executions with an error so callers don't hang forever
	for (const [id, pending] of pendingExecutions) {
		pending.resolve({
			stdout: pending.stdout.join('\n'),
			stderr: pending.stderr.join('\n'),
			plots: pending.plots,
			error: { message: 'Worker terminated' },
			duration: Date.now() - pending.startTime
		});
	}
	pendingExecutions.clear();

	updateState({ status: 'idle', progress: '', error: null });
}

// Re-export types and store
export type { ExecutionResult, PyodideState, PyodideStatus, PackageVersions, PyodidePackageInfo } from './types';
export { pyodideState } from '$lib/stores/pyodideStore';
