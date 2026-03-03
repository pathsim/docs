<script lang="ts">
	import { onDestroy } from 'svelte';
	import { base } from '$app/paths';
	import { Notebook } from '$lib/components/notebook';
	import NotebookControls from '$lib/components/notebook/NotebookControls.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { packageVersionsStore } from '$lib/stores/packageVersionsStore';
	import { exampleGroupsStore } from '$lib/stores/examplesContext';
	import { notebookStore } from '$lib/stores/notebookStore';
	import { groupByCategory } from '$lib/notebook/manifest';
	import { packages } from '$lib/config/packages';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// Base path for the version content
	let versionBasePath = $derived(`${base}/${data.packageId}/${data.tag}`);

	// Base path for figures: /{package}/{tag}/figures/
	let figuresBasePath = $derived(`${versionBasePath}/figures`);

	// Set package config for Pyodide execution
	// Pyodide will lazily reinitialize on next execution if packages/versions changed
	$effect(() => {
		const versionNumber = data.tag.replace(/^v/, '');
		const pkg = packages[data.packageId];

		// Build version map: pin the primary package to the selected version
		const pipName = pkg.installation.find((i) => i.name.toLowerCase() === 'pip')?.command.split(' ').pop() || data.packageId;
		const versions: Record<string, string> = { [pipName]: versionNumber };

		packageVersionsStore.set({
			packages: pkg.pyodidePackages,
			versions
		});

		return () => {
			packageVersionsStore.clear();
		};
	});

	// Reset Pyodide namespace when example changes (but don't terminate)
	$effect(() => {
		const slug = data.meta.slug;

		// Reset namespace when switching examples
		// Note: {#key} on Notebook handles component destruction and store cleanup
		return async () => {
			try {
				const { reset } = await import('$lib/pyodide');
				await reset();
			} catch {
				// Ignore if Pyodide not loaded
			}
			notebookStore.reset();
		};
	});

	// Populate examples store for sidebar TOC
	$effect(() => {
		if (data.versionManifest) {
			const grouped = groupByCategory(
				data.versionManifest.notebooks,
				data.versionManifest.categories
			);
			const groups = [...grouped.entries()].map(([category, notebooks]) => ({
				category,
				notebooks
			}));
			exampleGroupsStore.set(groups);
		}
	});

	onDestroy(() => {
		exampleGroupsStore.set([]);
	});
</script>

<svelte:head>
	<title>{data.meta.title} - Example</title>
	<meta name="description" content={data.meta.description} />
</svelte:head>

<Tooltip />

<div class="notebook-page">
	<NotebookControls
		viewOnly={!data.meta.executable}
		downloadUrl={`${versionBasePath}/notebooks/${data.meta.file}`}
	/>

	{#key data.meta.slug}
		<Notebook
			notebook={data.notebook}
			basePath={versionBasePath}
			precomputedOutputs={data.outputs}
			{figuresBasePath}
			showStaticOutputs={true}
			executable={data.meta.executable}
		/>
	{/key}
</div>

<style>
	.notebook-page {
		max-width: var(--content-max-width);
		min-width: 0;
		padding-bottom: var(--space-4xl);
	}
</style>
