<script lang="ts">
	import { onDestroy } from 'svelte';
	import { base } from '$app/paths';
	import Icon from '$lib/components/common/Icon.svelte';
	import Tooltip, { tooltip } from '$lib/components/common/Tooltip.svelte';
	import NotebookCell from '$lib/components/common/NotebookCell.svelte';
	import { packages, type PackageId, type InstallOption } from '$lib/config/packages';
	import { copyToClipboard } from '$lib/utils/clipboard';
	import { type PackageManifest, versionHasExamples, packageHasRoadmap } from '$lib/api/versions';
	import { packageVersionsStore } from '$lib/stores/packageVersionsStore';

	/**
	 * Compare semantic version strings (without 'v' prefix).
	 * Returns true if version >= minVersion.
	 */
	function versionSatisfiesMin(version: string, minVersion: string): boolean {
		const v = version.split('.').map(Number);
		const m = minVersion.split('.').map(Number);
		for (let i = 0; i < Math.max(v.length, m.length); i++) {
			const vPart = v[i] ?? 0;
			const mPart = m[i] ?? 0;
			if (vPart > mPart) return true;
			if (vPart < mPart) return false;
		}
		return true; // Equal versions
	}

	interface Props {
		packageId: PackageId;
		manifest?: PackageManifest | null;
		selectedTag?: string | null;
	}

	let { packageId, manifest = null, selectedTag = null }: Props = $props();

	let pkg = $derived(packages[packageId]);
	let featureCols = $derived(pkg.features.length > 4 ? 'cols-3' : 'cols-2');

	// Set package config for Pyodide so quickstart cells can execute
	$effect(() => {
		if (pkg.quickstart && pkg.pyodidePackages.length > 0) {
			const versionNumber = selectedTag?.replace(/^v/, '');
			const pipName = pkg.installation.find((i) => i.name.toLowerCase() === 'pip')?.command.split(' ').pop() || packageId;
			const versions: Record<string, string> = versionNumber ? { [pipName]: versionNumber } : {};

			packageVersionsStore.set({
				packages: pkg.pyodidePackages,
				versions
			});
		}

		return () => {
			packageVersionsStore.clear();
		};
	});

	onDestroy(() => {
		packageVersionsStore.clear();
	});

	// Track copy state for each install option
	let copiedStates = $state<Record<string, boolean>>({});

	function handleCopy(command: string, name: string) {
		copyToClipboard(
			command,
			() => (copiedStates[name] = true),
			() => (copiedStates[name] = false)
		);
	}

	// Reactively compute availability based on manifest and selectedTag
	let apiAvailable = $derived(manifest !== null && selectedTag !== null);
	let examplesAvailable = $derived(
		manifest && selectedTag ? versionHasExamples(selectedTag, manifest) : false
	);
	let roadmapAvailable = $derived(manifest ? packageHasRoadmap(manifest) : false);

	// Check if conda is available for this version
	let condaAvailable = $derived.by(() => {
		if (!pkg.conda) return false;
		const condaOption = pkg.installation.find((opt) => opt.name.toLowerCase() === 'conda');
		if (!condaOption?.minVersion) return true;
		if (!selectedTag) return true;
		const version = selectedTag.replace(/^v/, '');
		return versionSatisfiesMin(version, condaOption.minVersion);
	});

	// Build versioned paths
	let apiPath = $derived(selectedTag ? `${base}/${packageId}/${selectedTag}/api` : `${base}/${pkg.api}`);
	let examplesPath = $derived(selectedTag ? `${base}/${packageId}/${selectedTag}/examples` : pkg.examples ? `${base}/${pkg.examples}` : null);

	// Build versioned installation commands
	let versionNumber = $derived(selectedTag ? selectedTag.replace(/^v/, '') : null);
	let versionedInstallation = $derived(
		pkg.installation
			// Filter out options that don't meet minVersion requirement
			.filter((option) => {
				if (!option.minVersion || !versionNumber) return true;
				return versionSatisfiesMin(versionNumber, option.minVersion);
			})
			// Add version specifier to commands
			.map((option) => {
				if (!versionNumber) return option;

				let command = option.command;
				// Add version specifier based on package manager
				if (option.name.toLowerCase() === 'pip') {
					// pip uses == for version
					command = command.replace(/(\s)$/, '') + `==${versionNumber}`;
				} else if (option.name.toLowerCase() === 'conda') {
					// conda uses = for version
					command = command.replace(/(\s)$/, '') + `=${versionNumber}`;
				}
				return { ...option, command };
			})
	);
</script>

<svelte:head>
	<title>{pkg.name} — PathSim Docs</title>
	<meta name="description" content="{pkg.name} - {pkg.description}" />
	<link rel="canonical" href="https://docs.pathsim.org/{packageId}" />
</svelte:head>

<Tooltip />

<div class="hero">
	<img src="{base}/{pkg.logo}" alt={pkg.name} class="hero-logo" />
	<p class="description">{pkg.description}</p>
	<div class="hero-actions">
		{#if apiAvailable}
			<a href={apiPath} class="action-card">
				<Icon name="braces" size={20} />
				<span class="action-label">API</span>
			</a>
		{/if}
		{#if examplesAvailable && examplesPath}
			<a href={examplesPath} class="action-card">
				<Icon name="play" size={20} />
				<span class="action-label">Examples</span>
			</a>
		{/if}
		{#if roadmapAvailable}
			<a href="{base}/{packageId}/roadmap" class="action-card">
				<Icon name="roadmap" size={20} />
				<span class="action-label">Roadmap</span>
			</a>
		{/if}
		<a href={pkg.github} class="action-card">
			<Icon name="github" size={20} />
			<span class="action-label">GitHub</span>
		</a>
		{#if pkg.pypi}
			<a href={pkg.pypi} class="action-card">
				<Icon name="package" size={20} />
				<span class="action-label">PyPI</span>
			</a>
		{/if}
		{#if condaAvailable && pkg.conda}
			<a href={pkg.conda} class="action-card">
				<Icon name="package" size={20} />
				<span class="action-label">Conda</span>
			</a>
		{/if}
	</div>
</div>

{#if pkg.features.length > 0}
	<h2 id="key-features">Key Features</h2>

	<div class="tile-grid {featureCols}">
		{#each pkg.features as feature}
			<div class="tile elevated">
				<div class="panel-header">{feature.title}</div>
				<div class="panel-body tile-body">{feature.description}</div>
			</div>
		{/each}
	</div>
{/if}

{#if versionedInstallation.length > 0}
	<h2 id="installation">Installation</h2>

	<div class="install-grid">
		{#each versionedInstallation as option}
			<button class="install-card elevated" onclick={() => handleCopy(option.command, option.name)}>
				<div class="panel-header">
					<span>{option.name}</span>
					<div class="header-actions">
						<span class="icon-btn" class:copied={copiedStates[option.name]} use:tooltip={copiedStates[option.name] ? 'Copied!' : 'Copy'}>
							<Icon name={copiedStates[option.name] ? 'check' : 'copy'} size={14} />
						</span>
					</div>
				</div>
				<div class="install-body">
					<code>{option.command}</code>
				</div>
			</button>
		{/each}
	</div>
{/if}

{#if pkg.quickstart}
	<h2 id="quick-start">Quick Start</h2>

	<p class="quickstart-description">{pkg.quickstart.description}</p>

	<NotebookCell
		id="quickstart"
		code={pkg.quickstart.code}
		title={pkg.quickstart.title || 'Python'}
		editable={true}
	/>
{/if}

<div class="page-bottom-spacer"></div>

<style>
	.quickstart-description {
		color: var(--text-muted);
	}

	.page-bottom-spacer {
		height: var(--space-2xl);
	}
</style>
