import { error } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';
import { packages, type PackageId } from '$lib/config/packages';
import { getPackageManifest } from '$lib/api/versions';

const validPackageIds = new Set<string>(Object.keys(packages));

/**
 * Top-level loader for an unversioned package URL like /pathsim or /batt.
 * Loads the package manifest and picks the latest tag
 * so the overview page can show the version selector + sidebar links.
 *
 * The deeper /[package]/[version]/ layout supersedes the `selectedTag` value
 * with its own `resolvedTag` once a specific version is selected via the URL.
 */
export const load: LayoutLoad = async ({ params, fetch }) => {
	const packageId = params.package;

	if (!validPackageIds.has(packageId)) {
		throw error(404, `Package '${packageId}' not found`);
	}

	try {
		const manifest = await getPackageManifest(packageId, fetch);
		const selectedTag = manifest.latestTag;

		return {
			packageId: packageId as PackageId,
			manifest,
			selectedTag
		};
	} catch {
		// Manifest fetch failed — render overview without version selector.
		return {
			packageId: packageId as PackageId,
			manifest: undefined,
			selectedTag: undefined
		};
	}
};
