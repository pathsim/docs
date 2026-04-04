/**
 * Notebook Execution Store
 * Manages cell registry, execution state, and prerequisite resolution
 */

import { writable, get } from 'svelte/store';

export type CellStatus = 'idle' | 'pending' | 'running' | 'success' | 'error';

export interface CellState {
	id: string;
	status: CellStatus;
	executionCount: number;
	/** Function to execute this cell (registered by NotebookCell) */
	execute: () => Promise<void>;
	/** IDs of cells this cell depends on */
	prerequisites: string[];
}

/**
 * Notebook state containing all registered cells.
 *
 * Note: Updates to `cells` always create a new Map instance (immutable pattern).
 * This is intentional for Svelte's reactivity system - the store needs a new
 * reference to trigger subscribers. While this creates some overhead, it
 * ensures reliable reactivity and simplifies debugging.
 */
interface NotebookState {
	/** Registry of all cells by ID */
	cells: Map<string, CellState>;
	/** Global lock to prevent overlapping execution chains */
	executing: boolean;
}

const initialState: NotebookState = {
	cells: new Map(),
	executing: false
};

function createNotebookStore() {
	const { subscribe, set, update } = writable<NotebookState>(initialState);

	/**
	 * Detect circular dependencies using DFS
	 */
	function detectCircularDeps(
		cellId: string,
		cells: Map<string, CellState>,
		visited: Set<string> = new Set(),
		path: Set<string> = new Set()
	): string[] | null {
		if (path.has(cellId)) {
			// Found cycle - return the cycle path
			return [...path, cellId];
		}
		if (visited.has(cellId)) {
			return null; // Already checked this branch
		}

		visited.add(cellId);
		path.add(cellId);

		const cell = cells.get(cellId);
		if (cell) {
			for (const prereqId of cell.prerequisites) {
				const cycle = detectCircularDeps(prereqId, cells, visited, path);
				if (cycle) return cycle;
			}
		}

		path.delete(cellId);
		return null;
	}

	/**
	 * Get execution order for a cell and its prerequisites (topological sort)
	 */
	function getExecutionOrder(
		cellId: string,
		cells: Map<string, CellState>,
		visited: Set<string> = new Set()
	): string[] {
		if (visited.has(cellId)) return [];
		visited.add(cellId);

		const cell = cells.get(cellId);
		if (!cell) return [];

		const order: string[] = [];

		// First, add prerequisites (depth-first)
		for (const prereqId of cell.prerequisites) {
			order.push(...getExecutionOrder(prereqId, cells, visited));
		}

		// Then add this cell
		order.push(cellId);

		return order;
	}

	return {
		subscribe,

		/**
		 * Register a cell with the store
		 */
		registerCell(
			id: string,
			execute: () => Promise<void>,
			prerequisites: string[] = []
		) {
			update((state) => {
				const cells = new Map(state.cells);
				cells.set(id, {
					id,
					status: 'idle',
					executionCount: 0,
					execute,
					prerequisites
				});
				return { ...state, cells };
			});
		},

		/**
		 * Unregister a cell (on component destroy)
		 */
		unregisterCell(id: string) {
			update((state) => {
				const cells = new Map(state.cells);
				cells.delete(id);
				return { ...state, cells };
			});
		},

		/**
		 * Update cell status
		 */
		setCellStatus(id: string, status: CellStatus) {
			update((state) => {
				const cells = new Map(state.cells);
				const cell = cells.get(id);
				if (cell) {
					cells.set(id, { ...cell, status });
				}
				return { ...state, cells };
			});
		},

		/**
		 * Increment execution count for a cell
		 */
		incrementExecutionCount(id: string) {
			update((state) => {
				const cells = new Map(state.cells);
				const cell = cells.get(id);
				if (cell) {
					cells.set(id, { ...cell, executionCount: cell.executionCount + 1 });
				}
				return { ...state, cells };
			});
		},

		/**
		 * Get cell state by ID
		 */
		getCell(id: string): CellState | undefined {
			return get({ subscribe }).cells.get(id);
		},

		/**
		 * Check if a cell has been successfully executed
		 */
		isExecuted(id: string): boolean {
			const cell = get({ subscribe }).cells.get(id);
			return cell?.status === 'success';
		},

		/**
		 * Run a cell with automatic prerequisite execution
		 * @param cellId - The cell to run
		 * @param forcePrerequisites - If true, always re-run prerequisites even if already successful
		 * Returns list of cells that were run (in order)
		 */
		async runWithPrerequisites(
			cellId: string,
			forcePrerequisites: boolean = false
		): Promise<{
			success: boolean;
			executedCells: string[];
			error?: string;
		}> {
			const state = get({ subscribe });
			const cells = state.cells;

			// Prevent overlapping execution chains
			if (state.executing) {
				return {
					success: false,
					executedCells: [],
					error: 'Another execution is already in progress'
				};
			}

			// Check for circular dependencies
			const cycle = detectCircularDeps(cellId, cells);
			if (cycle) {
				return {
					success: false,
					executedCells: [],
					error: `Circular dependency detected: ${cycle.join(' → ')}`
				};
			}

			// Get execution order
			const executionOrder = getExecutionOrder(cellId, cells);

			// Filter to only cells that need to run
			const cellsToRun = forcePrerequisites
				? executionOrder // Run all cells in order when forcing
				: executionOrder.filter((id) => {
						const cell = cells.get(id);
						// Run if not yet successful, or if it's the target cell (always re-run target)
						return cell && (cell.status !== 'success' || id === cellId);
					});

			// Acquire execution lock
			update((s) => ({ ...s, executing: true }));

			// Mark all cells as pending
			for (const id of cellsToRun) {
				this.setCellStatus(id, 'pending');
			}

			const executedCells: string[] = [];

			try {
				// Execute in order
				for (const id of cellsToRun) {
					const cell = get({ subscribe }).cells.get(id);
					if (!cell) continue;

					this.setCellStatus(id, 'running');

					try {
						await cell.execute();
						// Status will be set to 'success' or 'error' by the cell itself
						const updatedCell = get({ subscribe }).cells.get(id);
						if (updatedCell?.status === 'error') {
							// Stop execution chain on error
							// Reset remaining pending cells to idle
							for (const remainingId of cellsToRun) {
								const remaining = get({ subscribe }).cells.get(remainingId);
								if (remaining?.status === 'pending') {
									this.setCellStatus(remainingId, 'idle');
								}
							}
							return {
								success: false,
								executedCells,
								error: `Cell "${id}" failed`
							};
						}
						executedCells.push(id);
					} catch (err) {
						this.setCellStatus(id, 'error');
						// Reset remaining pending cells
						for (const remainingId of cellsToRun) {
							const remaining = get({ subscribe }).cells.get(remainingId);
							if (remaining?.status === 'pending') {
								this.setCellStatus(remainingId, 'idle');
							}
						}
						return {
							success: false,
							executedCells,
							error: err instanceof Error ? err.message : String(err)
						};
					}
				}

				return { success: true, executedCells };
			} finally {
				update((s) => ({ ...s, executing: false }));
			}
		},

		/**
		 * Run all registered cells in order
		 * Cells are executed based on their prerequisites (topological order)
		 */
		async runAll(): Promise<{
			success: boolean;
			executedCells: string[];
			error?: string;
		}> {
			const state = get({ subscribe });
			const cells = state.cells;

			if (cells.size === 0) {
				return { success: true, executedCells: [] };
			}

			// Prevent overlapping execution chains
			if (state.executing) {
				return {
					success: false,
					executedCells: [],
					error: 'Another execution is already in progress'
				};
			}

			// Get all cell IDs and build a combined execution order
			const allCellIds = [...cells.keys()];
			const visited = new Set<string>();
			const executionOrder: string[] = [];

			// Build execution order respecting all prerequisites
			for (const cellId of allCellIds) {
				const order = getExecutionOrder(cellId, cells, new Set(visited));
				for (const id of order) {
					if (!visited.has(id)) {
						visited.add(id);
						executionOrder.push(id);
					}
				}
			}

			// Acquire execution lock
			update((s) => ({ ...s, executing: true }));

			// Mark all cells as pending
			for (const id of executionOrder) {
				this.setCellStatus(id, 'pending');
			}

			const executedCells: string[] = [];

			try {
				// Execute in order
				for (const id of executionOrder) {
					const cell = get({ subscribe }).cells.get(id);
					if (!cell) continue;

					this.setCellStatus(id, 'running');

					try {
						await cell.execute();
						const updatedCell = get({ subscribe }).cells.get(id);
						if (updatedCell?.status === 'error') {
							// Reset remaining pending cells
							for (const remainingId of executionOrder) {
								const remaining = get({ subscribe }).cells.get(remainingId);
								if (remaining?.status === 'pending') {
									this.setCellStatus(remainingId, 'idle');
								}
							}
							return {
								success: false,
								executedCells,
								error: `Cell "${id}" failed`
							};
						}
						executedCells.push(id);
					} catch (err) {
						this.setCellStatus(id, 'error');
						for (const remainingId of executionOrder) {
							const remaining = get({ subscribe }).cells.get(remainingId);
							if (remaining?.status === 'pending') {
								this.setCellStatus(remainingId, 'idle');
							}
						}
						return {
							success: false,
							executedCells,
							error: err instanceof Error ? err.message : String(err)
						};
					}
				}

				return { success: true, executedCells };
			} finally {
				update((s) => ({ ...s, executing: false }));
			}
		},

		/**
		 * Get all registered cell IDs
		 */
		getAllCellIds(): string[] {
			return [...get({ subscribe }).cells.keys()];
		},

		/**
		 * Check if any cells are currently running or pending
		 */
		isExecuting(): boolean {
			const state = get({ subscribe });
			return state.executing;
		},

		/**
		 * Reset all cells (e.g., when navigating away)
		 */
		resetAllCells() {
			update((state) => {
				const cells = new Map(state.cells);
				for (const [id, cell] of cells) {
					cells.set(id, { ...cell, status: 'idle', executionCount: 0 });
				}
				return { ...state, cells };
			});
		},

		/**
		 * Full reset (clears everything)
		 */
		reset() {
			set(initialState);
		}
	};
}

export const notebookStore = createNotebookStore();
