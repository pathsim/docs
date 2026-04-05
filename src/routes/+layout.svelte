<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import { afterNavigate } from '$app/navigation';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import { Header, MobileDrawer } from '$lib/components/layout';
	import { packageOrder, type PackageId } from '$lib/config/packages';
	import { CDN } from '$lib/config/cdn';
	import { getPackageManifest } from '$lib/api/versions';
	import { initializeSearch } from '$lib/utils/search';
	import { initializeCrossref } from '$lib/utils/crossref';
	import { versionStore } from '$lib/stores/versionStore';

	let { children } = $props();

	let theme = $state<'dark' | 'light'>('dark');
	let mobileMenuOpen = $state(false);

	// Determine current package from URL
	let currentPackage = $derived.by(() => {
		const path = $page.url.pathname;
		for (const id of packageOrder) {
			if (path.startsWith(`${base}/${id}`)) {
				return id;
			}
		}
		return null;
	});

	onMount(() => {
		const urlTheme = new URL(window.location.href).searchParams.get('theme');
		if (urlTheme === 'dark' || urlTheme === 'light') {
			theme = urlTheme;
			localStorage.setItem('theme', urlTheme);
		} else {
			const saved = localStorage.getItem('theme');
			if (saved === 'light' || saved === 'dark') {
				theme = saved;
			} else if (window.matchMedia('(prefers-color-scheme: light)').matches) {
				theme = 'light';
			}
		}
		document.documentElement.setAttribute('data-theme', theme);

		// Initialize version store from localStorage
		versionStore.initialize();

		// Initialize search indexes for all packages
		initializeAllPackageIndexes();
	});

	async function initializeAllPackageIndexes() {
		// Fetch all package versions in parallel
		const packagePromises = packageOrder.map(async (pkgId) => {
			// Check stored version first
			let tag = versionStore.getVersion(pkgId);
			if (!tag) {
				try {
					const manifest = await getPackageManifest(pkgId, fetch);
					tag = manifest.latestTag;
				} catch {
					return null; // Package not available
				}
			}
			return { packageId: pkgId, tag };
		});

		const results = await Promise.all(packagePromises);
		const packages = results.filter((p): p is { packageId: PackageId; tag: string } => p !== null);

		// Initialize search and crossref with all packages
		await Promise.all([initializeSearch(packages), initializeCrossref(packages)]);
	}

	function toggleTheme(e: MouseEvent) {
		const apply = () => {
			theme = theme === 'dark' ? 'light' : 'dark';
			document.documentElement.setAttribute('data-theme', theme);
			localStorage.setItem('theme', theme);
		};

		if (!document.startViewTransition) { apply(); return; }

		const x = e.clientX, y = e.clientY;
		const maxRadius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
		const transition = document.startViewTransition(apply);
		transition.ready.then(() => {
			document.documentElement.animate(
				{ clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${maxRadius}px at ${x}px ${y}px)`] },
				{ duration: 500, easing: 'ease-out', pseudoElement: '::view-transition-new(root)' }
			);
		});
	}

	function openMobileMenu() {
		mobileMenuOpen = true;
	}

	function closeMobileMenu() {
		mobileMenuOpen = false;
	}

	// Close mobile menu on navigation
	$effect(() => {
		$page.url.pathname;
		mobileMenuOpen = false;
	});

	// Scroll to top on navigation
	afterNavigate(() => {
		// Find scrollable content areas and reset their scroll position
		const scrollables = document.querySelectorAll('.doc-main, .page-wrapper');
		scrollables.forEach((el) => {
			if (el instanceof HTMLElement) {
				el.scrollTop = 0;
			}
		});
		// Also reset window scroll as fallback
		window.scrollTo(0, 0);
	});
</script>

<svelte:head>
	<link rel="stylesheet" href={CDN.katex.css} />
	{@html `<script type="application/ld+json">${JSON.stringify({
		"@context": "https://schema.org",
		"@type": "WebSite",
		"url": "https://docs.pathsim.org",
		"name": "PathSim Documentation",
		"description": "API reference, examples, and guides for PathSim — a Python framework for simulating dynamical systems using block diagrams."
	})}</script>`}
</svelte:head>

<Tooltip />

<a href="#main-content" class="skip-link">Skip to main content</a>

<div class="app">
	<Header onMenuClick={openMobileMenu} onThemeToggle={toggleTheme} {theme} />
	<div id="main-content" class="main-content">
		{@render children()}
	</div>
</div>

<MobileDrawer open={mobileMenuOpen} packageId={currentPackage} onClose={closeMobileMenu} />

<style>
	.app {
		height: 100vh;
		min-width: var(--app-min-width);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.main-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		min-height: 0;
		min-width: 0;
	}
</style>
