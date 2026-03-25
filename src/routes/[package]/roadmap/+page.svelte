<script lang="ts">
	import { base } from '$app/paths';
	import { packages, type PackageId } from '$lib/config/packages';
	import MarkdownRenderer from '$lib/components/common/MarkdownRenderer.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let pkg = $derived(packages[data.packageId as PackageId]);

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}
</script>

<svelte:head>
	<title>{pkg.name} Roadmap — PathSim Docs</title>
	<meta name="description" content="{pkg.name} development roadmap — upcoming features and planned improvements." />
	<link rel="canonical" href="https://docs.pathsim.org/{data.packageId}/roadmap" />
</svelte:head>

<div class="hero">
	<img src="{base}/{pkg.logo}" alt={pkg.name} class="hero-logo" />
	<p class="description">Development roadmap for {pkg.name}.</p>
</div>

{#if data.roadmap && data.roadmap.issues.length > 0}
	<div class="roadmap-meta">
		Last updated {formatDate(data.roadmap.updated)}
	</div>

	<div class="roadmap-list">
		{#each data.roadmap.issues as issue}
			<a
				href={issue.url}
				target="_blank"
				rel="noopener noreferrer"
				class="tile elevated roadmap-tile"
			>
				<div class="panel-header">
					<span class="issue-title">{issue.title}</span>
					<span class="issue-date">{formatDate(issue.created)}</span>
				</div>
				<div class="panel-body tile-body">
					{#if issue.labels.length > 0}
						<div class="issue-labels">
							{#each issue.labels as label}
								<span class="badge">{label}</span>
							{/each}
						</div>
					{/if}
					{#if issue.body}
						<div class="issue-body">
							<MarkdownRenderer markdown={issue.body} />
						</div>
					{/if}
				</div>
			</a>
		{/each}
	</div>
{:else}
	<div class="tile placeholder-tile">
		<div class="panel-body tile-body">No roadmap items available.</div>
	</div>
{/if}

<div class="page-bottom-spacer"></div>

<style>
	.page-bottom-spacer {
		height: var(--space-2xl);
	}

	.roadmap-meta {
		color: var(--text-disabled);
		font-size: var(--font-sm);
		margin-bottom: var(--space-lg);
	}

	.roadmap-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}

	.roadmap-tile {
		text-decoration: none;
		color: inherit;
		cursor: pointer;
	}

	.roadmap-tile:hover {
		text-decoration: none;
	}

	.roadmap-tile .panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-sm);
	}

	.issue-title {
		font-weight: 600;
	}

	.issue-date {
		color: var(--text-disabled);
		font-size: var(--font-sm);
		flex-shrink: 0;
	}

	.issue-labels {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-xs);
		margin-bottom: var(--space-sm);
	}

	.issue-body {
		color: var(--text-muted);
		font-size: var(--font-sm);
		line-height: 1.6;
	}
</style>
