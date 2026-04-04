<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import Icon from '$lib/components/common/Icon.svelte';
	import Tooltip, { tooltip } from '$lib/components/common/Tooltip.svelte';
	import { packages, packageOrder, nav, type PackageId } from '$lib/config/packages';
	import type { SearchResult } from '$lib/utils/search';
	import { createDebouncedSearch } from '$lib/stores/searchHook.svelte';
	import { searchTarget } from '$lib/stores/searchNavigation';
	import { getPackageManifest, packageHasRoadmap } from '$lib/api/versions';
	import { SearchResult as SearchResultComponent } from '$lib/components/search';

	function navigateWithTransition(path: string) {
		const doc = document as Document & {
			startViewTransition?: (cb: () => Promise<void>) => { finished: Promise<void> };
		};

		if (!doc.startViewTransition) {
			goto(path);
			return;
		}

		doc.startViewTransition(() => goto(path).then(() => {}));
	}

	// Use shared search hook
	const searchState = createDebouncedSearch({ limit: 8 });
	let searchInput = $state<HTMLInputElement | null>(null);

	function handleGlobalKeydown(event: KeyboardEvent) {
		if ((event.ctrlKey || event.metaKey) && event.key === 'f') {
			event.preventDefault();
			searchInput?.focus();
		}
	}

	// Track which packages have roadmaps
	let roadmapFlags = $state<Record<string, boolean>>({});

	onMount(() => {
		window.addEventListener('keydown', handleGlobalKeydown);

		// Load manifests to check roadmap availability
		for (const pkgId of packageOrder) {
			getPackageManifest(pkgId, fetch)
				.then((manifest) => {
					roadmapFlags[pkgId] = packageHasRoadmap(manifest);
				})
				.catch(() => {});
		}

		return () => {
			window.removeEventListener('keydown', handleGlobalKeydown);
		};
	});

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
		searchTarget.set({
			name: result.name,
			type: result.type,
			parentClass: result.parentClass,
			source: 'search'
		});
		goto(`${base}/${result.path}`);
	}
</script>

<svelte:head>
	<title>PathSim Documentation — API Reference, Examples & Guides</title>
	<meta name="description" content="Documentation for PathSim — a Python framework for simulating dynamical systems using block diagrams. API reference, interactive examples, and guides." />
	<link rel="canonical" href="https://docs.pathsim.org/" />
</svelte:head>

<Tooltip />

<div class="page-wrapper">
	<main>
		<header class="hero">
			<img src="{base}/pathsim_logo.png" alt="PathSim" class="hero-logo" />
			<p class="tagline">Documentation for the PathSim ecosystem</p>
			<p class="description">
				API reference, tutorials, and examples for PathSim and its domain-specific toolboxes.
			</p>
			<div class="hero-search">
				<div class="search-box elevated">
					<Icon name="search" size={16} />
					<input
						type="text"
						placeholder="Search the API..."
						bind:value={searchState.query}
						bind:this={searchInput}
						onkeydown={handleSearchKeydown}
					/>
					{#if searchState.isSearching}
						<span class="search-spinner"></span>
					{:else if searchState.query}
						<button class="clear-btn" onclick={() => searchState.clear()}>
							<Icon name="x" size={14} />
						</button>
					{/if}
				</div>
			</div>
			<div class="hero-actions">
				<a href={nav.home} class="action-card">
					<Icon name="home" size={20} />
					<span class="action-label">Home</span>
				</a>
				<a href="{base}/{packages.pathsim.docs}" class="action-card">
					<Icon name="zap" size={20} />
					<span class="action-label">Intro</span>
				</a>
				<a href={nav.editor} class="action-card">
					<Icon name="play" size={20} />
					<span class="action-label">Editor</span>
				</a>
				<a href={nav.github} class="action-card">
					<Icon name="github" size={20} />
					<span class="action-label">GitHub</span>
				</a>
				<a href={nav.consulting} class="action-card">
					<Icon name="activity" size={20} />
					<span class="action-label">Support</span>
				</a>
			</div>
		</header>
	</main>

	<div class="separator"></div>

	{#if searchState.showResults}
		<main>
			<section class="search-results-section">
				<h2>Search Results</h2>
				{#if searchState.results.length > 0}
					<div class="results-grid">
						{#each searchState.results as result}
							<SearchResultComponent {result} variant="card" onclick={() => handleResultClick(result)} />
						{/each}
					</div>
				{:else}
					<div class="no-results">No results found for "{searchState.query}"</div>
				{/if}
			</section>
		</main>
		<div class="separator"></div>
	{/if}

	<main>
		<section class="packages">
		<h2>Packages</h2>
		<div class="package-grid">
			{#each packageOrder as pkgId}
				{@const pkg = packages[pkgId]}
				<div class="package-card elevated">
					<div class="card-info">
						<div class="card-info-row">
							<span>{pkg.shortName}</span>
							<div class="header-actions">
								<a href="{base}/{pkg.api}" class="icon-btn" use:tooltip={'API'}>
									<Icon name="braces" size={14} />
								</a>
								<a href="{base}/{pkg.docs}" class="icon-btn" use:tooltip={'Docs'}>
									<Icon name="book" size={14} />
								</a>
								{#if pkg.pypi}
									<a href={pkg.pypi} class="icon-btn" use:tooltip={'PyPI'}>
										<Icon name="package" size={14} />
									</a>
								{/if}
								{#if pkg.examples}
									<a href="{base}/{pkg.examples}" class="icon-btn" use:tooltip={'Examples'}>
										<Icon name="play" size={14} />
									</a>
								{/if}
								{#if roadmapFlags[pkgId]}
									<a href="{base}/{pkgId}/roadmap" class="icon-btn" use:tooltip={'Roadmap'}>
										<Icon name="roadmap" size={14} />
									</a>
								{/if}
								<a href={pkg.github} class="icon-btn" use:tooltip={'GitHub'}>
									<Icon name="github" size={14} />
								</a>
							</div>
						</div>
						<div class="card-description">{pkg.description}</div>
					</div>
					<button class="package-body" onclick={() => navigateWithTransition(`${base}/${pkg.docs}`)}>
						<img src="{base}/{pkg.logo}" alt={pkg.name} />
					</button>
				</div>
			{/each}
		</div>
		</section>
	</main>
</div>

<style>
	.page-wrapper {
		flex: 1;
		overflow-x: hidden;
		overflow-y: auto;
	}

	main {
		max-width: 1200px;
		margin: 0 auto;
		padding: 0 var(--space-lg);
	}

	.hero {
		text-align: center;
		padding: var(--space-2xl) 0;
	}

	.hero-logo {
		height: 140px;
		width: auto;
		margin-bottom: var(--space-lg);
	}

	.tagline {
		font-size: var(--font-lg);
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-bottom: var(--space-md);
	}

	.description {
		font-size: var(--font-base);
		color: var(--text-muted);
		margin-bottom: var(--space-2xl);
	}

	.hero-search {
		position: relative;
		max-width: 400px;
		margin: 0 auto var(--space-xl);
	}

	.search-box {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		padding: var(--space-sm) var(--space-md);
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: 9999px;
		color: var(--text-muted);
	}

	.search-box:focus-within {
		border-color: var(--accent);
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 25%, transparent);
	}

	.search-box input {
		flex: 1;
		background: transparent;
		border: none;
		box-shadow: none;
		font-size: var(--font-base);
		color: var(--text);
		outline: none;
	}

	.search-box input::placeholder {
		color: var(--text-muted);
	}

	.search-box .clear-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		background: none;
		border: none;
		color: var(--text-muted);
		padding: 2px;
		cursor: pointer;
	}

	.search-box .clear-btn:hover {
		color: var(--text);
	}

	/* Search Results Section */
	.search-results-section {
		padding: var(--space-xl) 0;
	}

	.results-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: var(--space-md);
	}

	@media (max-width: 1024px) {
		.results-grid {
			grid-template-columns: repeat(3, 1fr);
		}
	}

	@media (max-width: 768px) {
		.results-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (max-width: 480px) {
		.results-grid {
			grid-template-columns: 1fr;
		}
	}

	.no-results {
		padding: var(--space-xl);
		text-align: center;
		color: var(--text-muted);
		font-size: var(--font-base);
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
	}

	.hero-actions {
		display: flex;
		justify-content: center;
		flex-wrap: wrap;
		gap: var(--space-xs);
	}

	section {
		padding: var(--space-xl) 0;
	}

	h2 {
		font-size: var(--font-base);
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-bottom: var(--space-lg);
	}

	.package-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: var(--space-lg);
	}

	@media (max-width: 900px) {
		.package-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (max-width: 600px) {
		.package-grid {
			grid-template-columns: 1fr;
		}

		main {
			padding: 0 var(--space-md);
		}

		.hero {
			padding: var(--space-xl) 0;
		}

		.hero-logo {
			height: 100px;
		}
	}

	.package-card {
		position: relative;
		border-radius: var(--radius-lg);
		border: 1px solid var(--border);
		overflow: hidden;
		transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
	}

	.package-card:hover {
		border-color: var(--accent);
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 25%, transparent);
	}

	.card-info {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		z-index: 1;
		padding: var(--space-sm) var(--space-lg);
		background: var(--surface-raised);
		border-bottom: 1px solid var(--border);
		border-radius: var(--radius-lg) var(--radius-lg) 0 0;
		font-size: var(--font-base);
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.card-info-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.card-description {
		font-size: var(--font-base);
		font-weight: 400;
		color: var(--text-muted);
		text-transform: none;
		letter-spacing: normal;
		max-height: 0;
		overflow: hidden;
		opacity: 0;
		transition: max-height 0.15s ease, opacity 0.15s ease, margin 0.15s ease;
	}

	.package-card:hover .card-description {
		max-height: 100px;
		opacity: 1;
		margin-top: 4px;
	}

	.header-actions {
		display: flex;
		gap: var(--space-xs);
	}

	.package-body {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		padding: var(--space-xl);
		padding-top: calc(40px + var(--space-xl));
		background: var(--surface);
		border: none;
		cursor: pointer;
		text-decoration: none;
	}

	.package-body img {
		height: 100px;
		width: auto;
		object-fit: contain;
	}
</style>
