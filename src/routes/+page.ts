import type { PageLoad } from './$types';
import { packageOrder, type PackageId } from '$lib/config/packages';
import {
	getPackageManifest,
	packageHasRoadmap,
	versionHasApi,
	versionHasExamples
} from '$lib/api/versions';

export interface PackageFlags {
	hasApi: boolean;
	hasExamples: boolean;
	hasRoadmap: boolean;
}

/**
 * Load each package's manifest at prerender time so the home page can
 * server-render the API / Examples / Roadmap icon links based on real
 * availability flags. Doing this client-side in onMount would emit the
 * icons only after hydration — and the adapter-static crawler would never
 * see the links, leaving the unversioned redirect routes unprerendered.
 */
export const load: PageLoad = async ({ fetch }) => {
	const entries = await Promise.all(
		packageOrder.map(async (pkgId) => {
			try {
				const manifest = await getPackageManifest(pkgId, fetch);
				const flags: PackageFlags = {
					hasApi: versionHasApi(manifest.latestTag, manifest),
					hasExamples: versionHasExamples(manifest.latestTag, manifest),
					hasRoadmap: packageHasRoadmap(manifest)
				};
				return [pkgId, flags] as const;
			} catch {
				// Manifest unavailable — hide every conditional link for this package.
				const flags: PackageFlags = { hasApi: false, hasExamples: false, hasRoadmap: false };
				return [pkgId, flags] as const;
			}
		})
	);

	const packageFlags = Object.fromEntries(entries) as Record<PackageId, PackageFlags>;

	return { packageFlags };
};
