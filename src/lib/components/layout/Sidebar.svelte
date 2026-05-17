<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import Icon from '$lib/components/common/Icon.svelte';
	import VersionSelector from './VersionSelector.svelte';
	import { getSidebarItems, type PackageId } from '$lib/config/packages';
	import { apiModulesStore } from '$lib/stores/apiContext';
	import { ApiToc } from '$lib/components/api';
	import ExamplesToc from '$lib/components/examples/ExamplesToc.svelte';
	import type { SearchResult } from '$lib/utils/search';
	import { createDebouncedSearch } from '$lib/stores/searchHook.svelte';
	import { searchTarget } from '$lib/stores/searchNavigation';
	import { exampleGroupsStore } from '$lib/stores/examplesContext';
	import type { PackageManifest } from '$lib/api/versions';
	import { versionHasExamples, versionHasApi, packageHasRoadmap } from '$lib/api/versions';
	import { SearchInput, SearchResult as SearchResultComponent } from '$lib/components/search';

	interface Props {
		packageId: PackageId;
		manifest?: PackageManifest;
		currentTag?: string;
	}

	let { packageId, manifest, currentTag }: Props = $props();

	// Check if current version has examples
	let hasExamples = $derived(
		manifest && currentTag ? versionHasExamples(currentTag, manifest) : false
	);

	// Check if current version has API (false for packages with no Python source)
	let hasApi = $derived(
		manifest && currentTag ? versionHasApi(currentTag, manifest) : !!manifest
	);

	// Check if package has roadmap items
	let hasRoadmap = $derived(manifest ? packageHasRoadmap(manifest) : false);

	// Filter sidebar items based on availability
	// - Hide API Reference if version has no extracted API
	// - Hide Examples if current version has no examples
	// - Hide Roadmap if package has no roadmap items
	let items = $derived(
		getSidebarItems(packageId, currentTag).filter(
			(item) =>
				(item.title !== 'API Reference' || hasApi) &&
				(item.title !== 'Examples' || hasExamples) &&
				(item.title !== 'Roadmap' || hasRoadmap)
		)
	);

	// Use shared search hook
	const searchState = createDebouncedSearch({ limit: 15 });
	let searchInput = $state<HTMLInputElement | null>(null);

	function handleGlobalKeydown(event: KeyboardEvent) {
		if ((event.ctrlKey || event.metaKey) && event.key === 'f') {
			event.preventDefault();
			searchInput?.focus();
		}
	}

	onMount(() => {
		window.addEventListener('keydown', handleGlobalKeydown);
		return () => {
			window.removeEventListener('keydown', handleGlobalKeydown);
		};
	});

	// Check if we're on an API page or examples page
	let isApiPage = $derived($page.url.pathname.includes('/api'));
	let isExamplesPage = $derived($page.url.pathname.includes('/examples'));
	let isVersionedPage = $derived(isApiPage || isExamplesPage);

	// Check if we're on an overview page (no /api or /examples in path)
	let isOverviewPage = $derived(!isApiPage && !$page.url.pathname.includes('/examples'));

	function isActive(path: string): boolean {
		return $page.url.pathname === `${base}/${path}`;
	}

	function handleSearchKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			if (searchState.query) {
				searchState.clear();
			} else {
				searchInput?.blur();
			}
			event.stopPropagation();
		}
	}

	function handleResultClick(result: SearchResult) {
		searchState.clear();
		// Set the target element to expand/scroll to
		searchTarget.set({
			name: result.name,
			type: result.type,
			parentClass: result.parentClass,
			source: 'search'
		});
		goto(`${base}/${result.path}`);
	}
</script>

<aside class="sidebar">
	<div class="sidebar-fixed">
		<div class="search-container">
			<SearchInput
				bind:value={searchState.query}
				bind:inputRef={searchInput}
				isSearching={searchState.isSearching}
				onkeydown={handleSearchKeydown}
			/>
		</div>

		{#if searchState.showResults}
			<nav class="sidebar-nav search-results">
				{#if searchState.results.length > 0}
					{#each searchState.results as result}
						<SearchResultComponent {result} variant="list" onclick={() => handleResultClick(result)} />
					{/each}
				{:else}
					<div class="no-results">No results found</div>
				{/if}
			</nav>
		{:else}
			<!-- Version selector - show whenever manifest is available -->
			{#if manifest && currentTag}
				<VersionSelector {packageId} {manifest} {currentTag} />
			{/if}

			<nav class="sidebar-nav">
				{#each items as item}
					<a href="{base}/{item.path}" class="sidebar-item" class:active={isActive(item.path)}>
						{#if item.icon}
							<Icon name={item.icon} size={14} />
						{/if}
						<span>{item.title}</span>
					</a>
				{/each}
			</nav>
		{/if}

	</div>

	{#if !searchState.showResults && isApiPage && $apiModulesStore.length > 0}
		<div class="sidebar-scrollable with-separator">
			<ApiToc modules={$apiModulesStore} />
		</div>
	{:else if !searchState.showResults && isExamplesPage && $exampleGroupsStore.length > 0}
		<div class="sidebar-scrollable with-separator">
			<ExamplesToc groups={$exampleGroupsStore} {packageId} currentTag={currentTag} />
		</div>
	{/if}
</aside>

<style>
	.sidebar {
		width: var(--sidebar-width);
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-right: 1px solid var(--border);
	}

	.sidebar-fixed {
		flex-shrink: 0;
	}

	.sidebar-scrollable {
		flex: 1;
		overflow-y: auto;
		min-height: 0;
	}

	.sidebar-scrollable.with-separator {
		border-top: 1px solid var(--border);
	}

	.search-container {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		height: var(--header-height);
		padding: 0 var(--space-md);
		border-bottom: 1px solid var(--border);
		transition:
			border-color var(--transition-fast),
			box-shadow var(--transition-fast);
	}

	.search-container:focus-within {
		box-shadow: inset 0 0 0 2px color-mix(in srgb, var(--accent) 25%, transparent);
	}

	.search-results {
		overflow-y: auto;
		max-height: calc(100vh - var(--header-height) - var(--header-height));
	}

	.no-results {
		padding: var(--space-lg);
		text-align: center;
		color: var(--text-muted);
		font-size: var(--font-base);
	}

	.sidebar-nav {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
		padding: var(--space-md);
	}

	.sidebar-item {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		padding: var(--space-sm) var(--space-md);
		font-size: var(--font-base);
		font-weight: 500;
		color: var(--text-muted);
		text-transform: uppercase;
		text-decoration: none;
		border-radius: var(--radius-sm);
		transition: all var(--transition-fast);
	}

	.sidebar-item:hover {
		color: var(--text);
		background: var(--surface-hover);
		text-decoration: none;
	}

	.sidebar-item.active {
		color: var(--accent);
		background: var(--accent-bg);
	}

	.sidebar-item :global(svg) {
		flex-shrink: 0;
	}
</style>
