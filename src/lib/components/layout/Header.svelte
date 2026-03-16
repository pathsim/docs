<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import Icon from '$lib/components/common/Icon.svelte';
	import { tooltip } from '$lib/components/common/Tooltip.svelte';
	import { packages, packageOrder, nav, type PackageId } from '$lib/config/packages';

	interface Props {
		onMenuClick?: () => void;
		onThemeToggle: () => void;
		theme: 'dark' | 'light';
	}

	let { onMenuClick, onThemeToggle, theme }: Props = $props();

	// Determine active package from current path
	let activePackage = $derived.by(() => {
		const path = $page.url.pathname;
		for (const id of packageOrder) {
			if (path.startsWith(`${base}/${id}`)) {
				return id;
			}
		}
		return null;
	});
</script>

<header>
	<div class="header-content">
		<div class="header-left">
			{#if onMenuClick}
				<button class="icon-btn menu-btn" onclick={onMenuClick} use:tooltip={'Menu'}>
					<Icon name="menu" size={14} />
				</button>
			{/if}
			<a href="{base}/" class="icon-btn" use:tooltip={'Docs'}>
				<Icon name="book" size={14} />
			</a>
			<nav class="package-tabs">
				{#each packageOrder as id}
					{@const pkg = packages[id]}
					<a
						href="{base}/{pkg.docs}"
						class="package-tab"
						class:active={activePackage === id}
						use:tooltip={pkg.name}
					>
						{pkg.shortName}
					</a>
				{/each}
			</nav>
		</div>
		<div class="header-right header-actions">
			<a href={nav.home} class="icon-btn" use:tooltip={'Home'}>
				<Icon name="home" size={14} />
			</a>
			<a href={nav.editor} class="icon-btn" use:tooltip={'Editor'}>
				<Icon name="play" size={14} />
			</a>
			<a href={nav.github} class="icon-btn" use:tooltip={'GitHub'}>
				<Icon name="github" size={14} />
			</a>
			<button class="icon-btn" onclick={onThemeToggle} use:tooltip={'Toggle theme'}>
				<Icon name={theme === 'dark' ? 'sun' : 'moon'} size={14} />
			</button>
		</div>
	</div>
</header>

<style>
	header {
		flex-shrink: 0;
		height: var(--header-height);
		background: var(--surface-raised);
		border-bottom: 1px solid var(--border);
	}

	.header-content {
		height: 100%;
		padding: 0 var(--space-lg);
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: var(--space-md);
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
	}

	.menu-btn {
		display: none;
	}

	@media (max-width: 768px) {
		.menu-btn {
			display: flex;
		}
	}

	.package-tabs {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
	}

	@media (max-width: 600px) {
		.package-tabs {
			display: none;
		}
	}

	/* Pill-style tabs matching pathview results panel */
	.package-tab {
		display: flex;
		align-items: center;
		gap: 6px;
		height: 24px;
		padding: 0 10px;
		font-size: var(--font-base);
		font-weight: 500;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		color: var(--text-muted);
		text-decoration: none;
		white-space: nowrap;
		transition: all var(--transition-fast);
	}

	.package-tab:hover {
		background: var(--surface-hover);
		border-color: var(--border-focus);
		color: var(--text);
		text-decoration: none;
	}

	.package-tab.active {
		background: color-mix(in srgb, var(--accent) 15%, var(--surface));
		border-color: var(--accent);
		color: var(--accent);
	}
</style>
