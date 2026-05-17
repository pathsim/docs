<script lang="ts">
	import { onDestroy } from 'svelte';
	import { base } from '$app/paths';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { packages, type PackageId } from '$lib/config/packages';
	import { groupByCategory, type NotebookMeta, type Category } from '$lib/notebook/manifest';
	import { exampleGroupsStore } from '$lib/stores/examplesContext';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let pkg = $derived(packages[data.packageId]);

	// Base path for example detail links — must be a real href so the
	// adapter-static crawler discovers each slug and prerenders it.
	let examplesBasePath = $derived(`${base}/${data.packageId}/${data.resolvedTag}/examples`);

	// Grouped notebooks from the version manifest
	let groupedNotebooks = $derived.by(() => {
		if (!data.versionManifest) return new Map<Category, NotebookMeta[]>();
		return groupByCategory(data.versionManifest.notebooks, data.versionManifest.categories);
	});

	// Reactively update store for sidebar TOC when data changes (including version changes)
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
		} else {
			exampleGroupsStore.set([]);
		}
	});

	onDestroy(() => {
		exampleGroupsStore.set([]);
	});

	function getThumbnailUrl(thumbnail: string): string {
		return `${base}/${data.packageId}/${data.resolvedTag}/figures/${thumbnail}`;
	}
</script>

<svelte:head>
	<title>{pkg.name} - Examples ({data.resolvedTag})</title>
	<meta name="description" content="{pkg.name} example notebooks" />
</svelte:head>

<Tooltip />

<div class="hero">
	<img src="{base}/{pkg.logo}" alt={pkg.name} class="hero-logo" />
	<p class="description">Interactive example notebooks for {pkg.name}.</p>
</div>

{#if data.versionManifest && data.versionManifest.notebooks.length > 0}
	{#each [...groupedNotebooks] as [category, notebooks]}
		<h2 id={category.id}>{category.title}</h2>

		<div class="tile-grid cols-2">
			{#each notebooks as notebook}
				<a href="{examplesBasePath}/{notebook.slug}" class="tile example-tile elevated">
					<div class="panel-header">{notebook.title}</div>
					<div class="panel-body tile-body">
						<p class="tile-description">{notebook.description}</p>
						{#if notebook.thumbnail}
							<div class="thumbnail-wrapper">
								<img src={getThumbnailUrl(notebook.thumbnail)} alt={notebook.title} />
							</div>
						{/if}
					</div>
				</a>
			{/each}
		</div>
	{/each}
{:else}
	<div class="tile placeholder-tile">
		<div class="panel-body tile-body">No examples available for this version.</div>
	</div>
{/if}

<div class="page-bottom-spacer"></div>

<style>
	.page-bottom-spacer {
		height: var(--space-2xl);
	}

	/* Example tile - real <a> link, but should look like the surrounding tiles */
	.example-tile {
		display: block;
		color: inherit;
		text-decoration: none;
	}

	.example-tile:hover {
		text-decoration: none;
	}

	/* Tile description text */
	.tile-description {
		margin: 0 0 var(--space-md) 0;
		color: var(--text-muted);
		font-size: var(--font-sm);
		line-height: 1.5;
	}

	/* Thumbnail wrapper and image */
	.thumbnail-wrapper {
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
	}

	.thumbnail-wrapper img {
		max-width: 100%;
		max-height: 180px;
		width: auto;
		height: auto;
		object-fit: contain;
		border-radius: var(--radius-sm);
	}
</style>
