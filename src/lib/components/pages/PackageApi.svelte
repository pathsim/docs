<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { base } from '$app/paths';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { packages, type PackageId } from '$lib/config/packages';
	import type { APIPackage, APIModule } from '$lib/api/generated';
	import { ModuleDoc } from '$lib/components/api';
	import { apiModulesStore } from '$lib/stores/apiContext';
	import { searchTarget } from '$lib/stores/searchNavigation';
	import { lookupRef } from '$lib/utils/crossref';
	import type { PackageManifest } from '$lib/api/versions';

	interface Props {
		packageId: PackageId;
		tag: string;
		manifest: PackageManifest;
		apiData: APIPackage;
	}

	let { packageId, tag, manifest, apiData }: Props = $props();

	let pkg = $derived(packages[packageId]);

	// Extract modules from API data, sorted alphabetically to match TOC order
	let modules = $derived(
		apiData
			? (Object.values(apiData.modules) as APIModule[]).sort((a, b) => a.name.localeCompare(b.name))
			: []
	);

	// Update the store with modules for the sidebar TOC
	$effect(() => {
		apiModulesStore.set(modules);
	});

	// Handle URL hash on page load - navigate to the target element
	onMount(() => {
		const hash = window.location.hash;
		if (hash) {
			const targetName = hash.slice(1); // Remove the '#'
			let ref = lookupRef(targetName);

			// If not found directly, search in the API data
			if (!ref && modules.length > 0) {
				// Check if target is in ClassName.methodName format
				const dotIndex = targetName.indexOf('.');
				const hasClassPrefix = dotIndex > 0 && dotIndex < targetName.length - 1;

				for (const mod of modules) {
					for (const cls of mod.classes) {
						// Check if it's this class
						if (cls.name === targetName) {
							ref = { name: cls.name, type: 'class', packageId, moduleName: mod.name, path: '' };
							break;
						}

						// Check methods - handle both ClassName.methodName and just methodName formats
						if (hasClassPrefix) {
							const [className, methodName] = [targetName.slice(0, dotIndex), targetName.slice(dotIndex + 1)];
							if (cls.name === className) {
								const method = cls.methods.find(m => m.name === methodName);
								if (method) {
									ref = { name: method.name, type: 'method', packageId, moduleName: mod.name, parentClass: cls.name, path: '' };
									break;
								}
							}
						} else {
							// Legacy: just method name
							const method = cls.methods.find(m => m.name === targetName);
							if (method) {
								ref = { name: method.name, type: 'method', packageId, moduleName: mod.name, parentClass: cls.name, path: '' };
								break;
							}
						}
					}
					if (ref) break;
					// Check module-level functions
					const func = mod.functions.find(f => f.name === targetName);
					if (func) {
						ref = { name: func.name, type: 'function', packageId, moduleName: mod.name, path: '' };
						break;
					}
				}
			}

			if (ref) {
				// Set searchTarget to trigger expansion and scroll
				searchTarget.set({
					name: ref.name,
					type: ref.type as 'class' | 'function' | 'method' | 'module',
					parentClass: ref.parentClass,
					source: 'url'
				});
			}
		}
	});

	// Clear the store when component unmounts
	onDestroy(() => {
		apiModulesStore.set([]);
	});
</script>

<svelte:head>
	<title>{pkg.name} API Reference{tag ? ` ${tag}` : ''} — PathSim Docs</title>
	<meta name="description" content="{pkg.name} API reference documentation — classes, methods, and parameters." />
	<link rel="canonical" href="https://docs.pathsim.org/{packageId}/latest/api" />
</svelte:head>

<Tooltip />

<div class="api-page">
	<div class="hero">
		<img src="{base}/{pkg.logo}" alt={pkg.name} class="hero-logo" />
		<p class="description">Click any class or function to expand its documentation. Use the sidebar to navigate between modules.</p>
	</div>

	<div class="separator"></div>

	{#if modules.length === 0}
		<div class="tile placeholder-tile">
			<div class="panel-body tile-body">
				No API documentation available yet. Run <code>npm run extract</code> to generate.
			</div>
		</div>
	{:else}
		<div class="api-content">
			{#each modules as module}
				<ModuleDoc {module} />
			{/each}
		</div>
	{/if}
</div>

<style>
	.api-page {
		position: relative;
	}

	.api-content {
		margin-top: var(--space-xl);
		padding-bottom: var(--space-2xl);
	}
</style>
