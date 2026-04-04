<script lang="ts">
	/**
	 * NotebookCell - Executable code cell for documentation notebooks
	 * Wraps CodeBlock with Pyodide execution, output display, and plot rendering
	 */
	import { onMount, onDestroy } from 'svelte';
	import { get } from 'svelte/store';
	import CodeBlock from './CodeBlock.svelte';
	import Icon from './Icon.svelte';
	import { tooltip } from './Tooltip.svelte';
	import { notebookStore, type CellStatus } from '$lib/stores/notebookStore';
	import { notebookSettingsStore } from '$lib/stores/notebookSettingsStore';
	import { pyodideState } from '$lib/stores/pyodideStore';
	import { packageVersionsStore } from '$lib/stores/packageVersionsStore';
	import CellOutput from '$lib/components/notebook/CellOutput.svelte';
	import LiveOutput from '$lib/components/notebook/LiveOutput.svelte';
	import type { CellOutput as CellOutputType } from '$lib/notebook/types';

	interface Props {
		/** Unique cell ID (required for prerequisite tracking) */
		id: string;
		/** The code to execute */
		code: string;
		/** Title shown in header */
		title?: string;
		/** Whether code can be edited */
		editable?: boolean;
		/** Whether code can be executed */
		executable?: boolean;
		/** IDs of cells that must execute first (will auto-run) */
		prerequisites?: string[];
		/** Static outputs from notebook file (shown before execution) */
		staticOutputs?: CellOutputType[];
		/** Pre-computed stdout from build */
		precomputedStdout?: string | null;
		/** Pre-computed stderr from build */
		precomputedStderr?: string | null;
		/** Figure URLs from pre-computed output */
		figureUrls?: string[];
		/** Callback to advance to next cell after execution */
		onadvance?: () => void;
	}

	let {
		id,
		code,
		title = 'Code',
		editable = false,
		executable = true,
		prerequisites = [],
		staticOutputs = [],
		precomputedStdout = null,
		precomputedStderr = null,
		figureUrls = [],
		onadvance = undefined
	}: Props = $props();

	// Reference to CodeBlock for getting current code and focusing
	let codeBlockRef = $state<{ getCurrentCode: () => string; focus: () => void } | undefined>(undefined);
	// Reference to container for scrolling
	let containerRef = $state<HTMLDivElement | undefined>(undefined);

	/** Focus this cell's editor and scroll into view */
	export function focus() {
		containerRef?.scrollIntoView({ behavior: 'smooth', block: 'center' });
		codeBlockRef?.focus();
	}

	// Execution output state
	let stdout = $state('');
	let stderr = $state('');
	let plots = $state<string[]>([]);
	let error = $state<{ message: string; traceback?: string } | null>(null);
	let duration = $state<number | null>(null);

	// Subscribe to cell state from store
	let cellState = $state<{ status: CellStatus; executionCount: number }>({
		status: 'idle',
		executionCount: 0
	});
	let globalExecuting = $state(false);

	// Computed states
	let isRunning = $derived(cellState.status === 'running');
	let isPending = $derived(cellState.status === 'pending');
	let isBlocked = $derived(globalExecuting && !isRunning && !isPending);
	let hasLiveOutput = $derived(stdout || stderr || plots.length > 0 || error);
	let hasPrecomputedOutput = $derived(
		precomputedStdout || precomputedStderr || figureUrls.length > 0
	);
	let showStaticOutputs = $derived(
		!hasLiveOutput && (staticOutputs.length > 0 || hasPrecomputedOutput)
	);
	let hasOutput = $derived(hasLiveOutput || showStaticOutputs);

	/**
	 * Execute this cell's code (called by store during prerequisite chain)
	 */
	async function executeCell(): Promise<void> {
		const codeToRun = codeBlockRef?.getCurrentCode() ?? code;

		// Clear previous output
		stdout = '';
		stderr = '';
		plots = [];
		error = null;
		duration = null;

		try {
			// Dynamically import pyodide
			const { execute, initPyodide } = await import('$lib/pyodide');

			// Get package config from store (set by example page)
			const config = get(packageVersionsStore);

			// Ensure Pyodide is initialized with the correct packages and versions
			pyodideState.setLoading('Initializing Python...');
			await initPyodide(
				config.packages.length > 0 ? config.packages : undefined,
				Object.keys(config.versions).length > 0 ? config.versions : undefined
			);
			pyodideState.setReady();

			// Execute with streaming callbacks for real-time output
			const result = await execute(codeToRun, {
				onStdout: (text) => {
					stdout = stdout ? stdout + '\n' + text : text;
				},
				onStderr: (text) => {
					stderr = stderr ? stderr + '\n' + text : text;
				},
				onPlot: (data) => {
					plots = [...plots, data];
				}
			});

			// Final result (in case any output was missed)
			stdout = result.stdout;
			stderr = result.stderr;
			plots = result.plots;
			duration = result.duration;

			if (result.error) {
				error = result.error;
				notebookStore.setCellStatus(id, 'error');
			} else {
				notebookStore.setCellStatus(id, 'success');
				notebookStore.incrementExecutionCount(id);
			}
		} catch (err) {
			error = {
				message: err instanceof Error ? err.message : String(err)
			};
			notebookStore.setCellStatus(id, 'error');
			throw err; // Re-throw to stop prerequisite chain
		}
	}

	/**
	 * Handle run button click - triggers prerequisite chain
	 */
	async function handleRun() {
		if (isRunning || isPending || globalExecuting) return;

		const settings = get(notebookSettingsStore);
		const result = await notebookStore.runWithPrerequisites(id, settings.forcePrerequisites);

		if (!result.success && result.error) {
			// Show error if it's a chain-level error (like circular deps)
			if (result.error.includes('Circular dependency')) {
				error = { message: result.error };
			}
		}
	}

	/**
	 * Handle run and advance - move to next cell immediately, then execute (Jupyter style)
	 */
	function handleRunAdvance() {
		// Advance to next cell immediately (don't wait for execution)
		onadvance?.();
		// Then trigger execution
		handleRun();
	}

	function clearOutput() {
		stdout = '';
		stderr = '';
		plots = [];
		error = null;
		duration = null;
	}

	// Register cell with store on mount
	onMount(() => {
		notebookStore.registerCell(id, executeCell, prerequisites);

		// Subscribe to cell state changes and global execution lock
		const unsubscribe = notebookStore.subscribe((state) => {
			const cell = state.cells.get(id);
			if (cell) {
				cellState = {
					status: cell.status,
					executionCount: cell.executionCount
				};
			}
			globalExecuting = state.executing;
		});

		return () => {
			unsubscribe();
		};
	});

	onDestroy(() => {
		notebookStore.unregisterCell(id);
	});
</script>

<div class="notebook-cell elevated" class:running={isRunning} class:pending={isPending} class:has-output={hasOutput} bind:this={containerRef}>
	<CodeBlock
		bind:this={codeBlockRef}
		{code}
		{title}
		editable={editable && executable}
		onrun={executable ? handleRun : undefined}
		onrunadvance={executable ? handleRunAdvance : undefined}
	>
		{#snippet headerActions()}
			{#if executable}
				{#if isRunning}
					<button class="icon-btn" disabled use:tooltip={'Running...'}>
						<Icon name="loader" size={14} />
					</button>
				{:else if isPending}
					<button class="icon-btn" disabled use:tooltip={'Waiting...'}>
						<Icon name="loader" size={14} />
					</button>
				{:else}
					<button class="icon-btn" onclick={handleRun} disabled={isBlocked} use:tooltip={isBlocked ? 'Execution in progress...' : 'Run cell'}>
						<Icon name="play" size={14} />
					</button>
				{/if}
			{/if}
		{/snippet}
	</CodeBlock>

	{#if hasOutput}
		<div class="output-section">
			{#if hasLiveOutput}
				<LiveOutput
					{error}
					{stdout}
					{stderr}
					{plots}
					{duration}
					onClear={clearOutput}
				/>
			{/if}

			{#if showStaticOutputs}
				<CellOutput
					outputs={staticOutputs}
					{figureUrls}
					{precomputedStdout}
					{precomputedStderr}
				/>
			{/if}
		</div>
	{/if}
</div>

<style>
	.notebook-cell {
		display: flex;
		flex-direction: column;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		overflow: hidden;
		min-width: 0;
		transition: border-color var(--transition-fast);
	}

	.notebook-cell.running {
		border-color: var(--accent);
	}

	.notebook-cell.pending {
		border-color: var(--text-muted);
		opacity: 0.8;
	}

	/* Focus highlight when editor is focused */
	.notebook-cell:focus-within {
		border-color: var(--accent);
		box-shadow: var(--shadow-md), 0 0 0 2px color-mix(in srgb, var(--accent) 25%, transparent);
	}

	.notebook-cell :global(.code-panel) {
		border: none;
		border-radius: 0;
	}

	/* Spinning loader for running/pending states only */
	.notebook-cell.running .icon-btn:disabled :global(svg),
	.notebook-cell.pending .icon-btn:disabled :global(svg) {
		animation: spin 1s linear infinite;
	}

	.notebook-cell.pending .icon-btn:disabled {
		opacity: 0.5;
	}

	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}

	/* Output section */
	.output-section {
		border-top: 1px solid var(--border);
	}
</style>
