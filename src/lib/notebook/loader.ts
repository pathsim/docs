/**
 * Notebook loading utilities for versioned content.
 *
 * Path structure:
 * - Version manifest: /{package}/{tag}/manifest.json
 * - Notebook source: /{package}/{tag}/notebooks/{file}
 * - Notebook outputs: /{package}/{tag}/outputs/{name}.json
 * - Figures: /{package}/{tag}/figures/{filename}
 */

import { base } from '$app/paths';
import type { RawNotebook } from './types';
import type { NotebookMeta, Category } from './manifest';
import { normalizeTag } from '$lib/api/versions';

// ============================================================================
// Types
// ============================================================================

export interface VersionManifest {
	package: string;
	tag: string;
	notebooks: NotebookMeta[];
	categories: Category[];
}

export interface CellOutputData {
	stdout: string | null;
	stderr: string | null;
	figures: string[];
}

export interface NotebookOutputs {
	cells: Record<string, CellOutputData>;
	executedAt: string;
	duration: number;
	success: boolean;
	error?: string;
}

// ============================================================================
// Loading Functions
// ============================================================================

/**
 * Load the version manifest (notebook list) for a specific version.
 * Path: /{package}/{tag}/manifest.json
 */
export async function getVersionManifest(
	packageId: string,
	tag: string,
	fetch: typeof globalThis.fetch
): Promise<VersionManifest> {
	const normalizedTag = normalizeTag(tag);
	const url = `${base}/${packageId}/${normalizedTag}/manifest.json`;
	const response = await fetch(url);

	if (!response.ok) {
		throw new Error(`Failed to load version manifest for ${packageId} ${normalizedTag}: ${response.status}`);
	}

	return response.json();
}

/**
 * Load notebook source (without outputs).
 * Path: /{package}/{tag}/notebooks/{file}
 */
export async function getNotebook(
	packageId: string,
	tag: string,
	file: string,
	fetch: typeof globalThis.fetch
): Promise<RawNotebook> {
	const normalizedTag = normalizeTag(tag);
	const url = `${base}/${packageId}/${normalizedTag}/notebooks/${file}`;
	const response = await fetch(url);

	if (!response.ok) {
		throw new Error(`Failed to load notebook ${file}: ${response.status}`);
	}

	return response.json();
}

/**
 * Load pre-computed outputs for a notebook.
 * Path: /{package}/{tag}/outputs/{name}.json
 */
export async function getNotebookOutputs(
	packageId: string,
	tag: string,
	notebookName: string,
	fetch: typeof globalThis.fetch
): Promise<NotebookOutputs | null> {
	const normalizedTag = normalizeTag(tag);
	const url = `${base}/${packageId}/${normalizedTag}/outputs/${notebookName}.json`;

	try {
		const response = await fetch(url);

		if (!response.ok) {
			// Outputs may not exist for all notebooks
			return null;
		}

		return response.json();
	} catch {
		return null;
	}
}

/**
 * Get the URL for a figure.
 * Path: /{package}/{tag}/figures/{filename}
 */
export function getFigureUrl(packageId: string, tag: string, filename: string): string {
	const normalizedTag = normalizeTag(tag);
	return `${base}/${packageId}/${normalizedTag}/figures/${filename}`;
}

/**
 * Load notebook with its pre-computed outputs.
 * Returns both the notebook source and outputs (if available).
 */
export async function getNotebookWithOutputs(
	packageId: string,
	tag: string,
	file: string,
	fetch: typeof globalThis.fetch
): Promise<{
	notebook: RawNotebook;
	outputs: NotebookOutputs | null;
}> {
	const notebookName = file.replace(/\.ipynb$/, '');

	const [notebook, outputs] = await Promise.all([
		getNotebook(packageId, tag, file, fetch),
		getNotebookOutputs(packageId, tag, notebookName, fetch)
	]);

	return { notebook, outputs };
}

/**
 * Find a notebook by slug in the manifest.
 */
export function findNotebookBySlug(
	manifest: VersionManifest,
	slug: string
): NotebookMeta | undefined {
	return manifest.notebooks.find((nb) => nb.slug === slug);
}

// groupByCategory lives in manifest.ts — this module focuses on data loading.
export { groupByCategory } from './manifest';
