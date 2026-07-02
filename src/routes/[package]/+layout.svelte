<script lang="ts">
	import { DocLayout } from '$lib/components/layout';
	import { page } from '$app/stores';
	import { packages, type PackageId } from '$lib/config/packages';
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();

	// Get packageId from route params, validate it exists
	let packageId = $derived($page.params.package as PackageId);
	let isValidPackage = $derived(packageId in packages);

	// Expose the active package on <html> so package-scoped theme overrides can
	// kick in (e.g. the FastSim red accent). Cleared when leaving package routes.
	$effect(() => {
		const el = document.documentElement;
		if (isValidPackage) {
			el.setAttribute('data-package', packageId);
		} else {
			el.removeAttribute('data-package');
		}
		return () => el.removeAttribute('data-package');
	});

	// Get version data from page.data. On a versioned URL ([version]/+layout.ts)
	// the active tag is exposed as `resolvedTag`; on the unversioned overview
	// ([package]/+layout.ts) it's `selectedTag`. Either is fine — pick the one
	// that's defined.
	let manifest = $derived($page.data.manifest);
	let currentTag = $derived($page.data.resolvedTag ?? $page.data.selectedTag);
</script>

{#if isValidPackage}
	<DocLayout {packageId} {manifest} {currentTag}>
		{@render children()}
	</DocLayout>
{:else}
	{@render children()}
{/if}
