// Version loading utilities for versioned API documentation
import { base } from '$app/paths';
import type { APIPackage } from './generated';

export interface VersionInfo {
	tag: string;
	released: string;
	hasExamples?: boolean;
	hasApi?: boolean;
}

export interface PackageManifest {
	package: string;
	latestTag: string;
	versions: VersionInfo[];
	hasRoadmap?: boolean;
}

/**
 * Fetch the package manifest (list of versions)
 * Path: /{package}/manifest.json
 */
export async function getPackageManifest(
	packageId: string,
	fetch: typeof globalThis.fetch
): Promise<PackageManifest> {
	const url = `${base}/${packageId}/manifest.json`;
	const response = await fetch(url);

	if (!response.ok) {
		throw new Error(`Failed to load package manifest for ${packageId}: ${response.status}`);
	}

	return response.json();
}

/**
 * Fetch API data for a specific package version
 * Path: /{package}/{tag}/api.json
 */
export async function getApiData(
	packageId: string,
	tag: string,
	fetch: typeof globalThis.fetch
): Promise<APIPackage> {
	const normalizedTag = normalizeTag(tag);
	const url = `${base}/${packageId}/${normalizedTag}/api.json`;
	const response = await fetch(url);

	if (!response.ok) {
		throw new Error(`Failed to load API data for ${packageId} ${normalizedTag}: ${response.status}`);
	}

	return response.json();
}

/**
 * Normalize a tag to have 'v' prefix
 */
export function normalizeTag(tag: string): string {
	return tag.startsWith('v') ? tag : `v${tag}`;
}

/**
 * Resolve a version/tag string to an actual tag
 * - 'latest' -> actual latest tag from manifest
 * - undefined -> actual latest tag from manifest
 * - 'v0.16.4' or '0.16.4' -> 'v0.16.4'
 */
export function resolveTag(tagOrVersion: string | undefined, manifest: PackageManifest): string {
	if (!tagOrVersion || tagOrVersion === 'latest') {
		return manifest.latestTag;
	}

	const normalized = normalizeTag(tagOrVersion);

	// Validate the tag exists in manifest
	const exists = manifest.versions.some((v) => v.tag === normalized);
	if (!exists) {
		throw new Error(`Version ${normalized} not found for ${manifest.package}`);
	}

	return normalized;
}

/**
 * Check if a tag is the latest tag
 */
export function isLatestTag(tag: string, manifest: PackageManifest): boolean {
	return normalizeTag(tag) === manifest.latestTag;
}

/**
 * Get the display label for a tag
 */
export function getTagLabel(tag: string, manifest: PackageManifest): string {
	if (isLatestTag(tag, manifest)) {
		return `${tag} (latest)`;
	}
	return tag;
}

/**
 * Check if a version has examples
 */
export function versionHasExamples(tag: string, manifest: PackageManifest): boolean {
	const normalized = normalizeTag(tag);
	const version = manifest.versions.find((v) => v.tag === normalized);
	return version?.hasExamples ?? false;
}

/**
 * Check if a version has an extracted API. Returns true when the flag is
 * missing (older manifests) so we err on the side of showing the link.
 */
export function versionHasApi(tag: string, manifest: PackageManifest): boolean {
	const normalized = normalizeTag(tag);
	const version = manifest.versions.find((v) => v.tag === normalized);
	return version?.hasApi ?? true;
}

/**
 * Check if a package has roadmap items
 */
export function packageHasRoadmap(manifest: PackageManifest): boolean {
	return manifest.hasRoadmap ?? false;
}
