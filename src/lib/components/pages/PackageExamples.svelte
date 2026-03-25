<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import Icon from '$lib/components/common/Icon.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { packages, type PackageId } from '$lib/config/packages';
	import {
		loadManifest,
		groupByCategory,
		type NotebookManifest,
		type NotebookMeta,
		type Category
	} from '$lib/notebook/manifest';
	import { exampleGroupsStore } from '$lib/stores/examplesContext';

	interface Props {
		packageId: PackageId;
	}

	let { packageId }: Props = $props();

	let pkg = $derived(packages[packageId]);

	// State
	let manifest = $state<NotebookManifest | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Grouped notebooks
	let groupedNotebooks = $derived.by(() => {
		if (!manifest) return new Map<Category, NotebookMeta[]>();
		return groupByCategory(manifest.notebooks, manifest.categories);
	});

	onMount(async () => {
		try {
			manifest = await loadManifest(packageId);
			// Populate store for sidebar TOC with grouped data
			if (manifest) {
				const grouped = groupByCategory(manifest.notebooks, manifest.categories);
				const groups = [...grouped.entries()].map(([category, notebooks]) => ({
					category,
					notebooks
				}));
				exampleGroupsStore.set(groups);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load examples';
		} finally {
			loading = false;
		}
	});

	onDestroy(() => {
		// Clear store when leaving page
		exampleGroupsStore.set([]);
	});
</script>

<svelte:head>
	<title>{pkg.name} Examples — PathSim Docs</title>
	<meta name="description" content="Interactive example notebooks for {pkg.name} — tutorials, simulations, and code walkthroughs." />
	<link rel="canonical" href="https://docs.pathsim.org/{packageId}/latest/examples" />
</svelte:head>

<Tooltip />

<div class="hero">
	<img src="{base}/{pkg.logo}" alt={pkg.name} class="hero-logo" />
	<p class="description">Interactive example notebooks for {pkg.name}.</p>
</div>

{#if loading}
	<div class="loading-centered">
		<Icon name="loader" size={24} />
		<span>Loading examples...</span>
	</div>
{:else if error}
	<div class="error-state">
		<Icon name="triangle-alert" size={24} />
		<span>{error}</span>
	</div>
{:else if manifest}
	{#each [...groupedNotebooks] as [category, notebooks]}
		<h2 id={category.id}>{category.title}</h2>

		<div class="tile-grid cols-3">
			{#each notebooks as notebook}
				<div
					class="tile example-tile elevated"
					onclick={() => goto(`${base}/${packageId}/examples/${notebook.slug}`)}
					onkeydown={(e) => e.key === 'Enter' && goto(`${base}/${packageId}/examples/${notebook.slug}`)}
					role="button"
					tabindex="0"
				>
					<div class="panel-header">{notebook.title}</div>
					<div class="panel-body tile-body">{notebook.description}</div>
				</div>
			{/each}
		</div>
	{/each}

	{#if manifest.notebooks.length === 0}
		<div class="tile placeholder-tile">
			<div class="panel-body tile-body">No examples available yet.</div>
		</div>
	{/if}
{/if}

<div class="page-bottom-spacer"></div>

<style>
	.page-bottom-spacer {
		height: var(--space-2xl);
	}
	/* Loading state */
	.loading-centered {
		gap: var(--space-md);
	}

	.loading-centered :global(svg) {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}

	/* Error state */
	.error-state {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-md);
		padding: var(--space-xl);
		color: var(--error);
	}

	/* Example tile - clickable */
	.example-tile {
		cursor: pointer;
	}
</style>
