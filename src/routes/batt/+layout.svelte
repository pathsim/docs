<script lang="ts">
	import { DocLayout } from '$lib/components/layout';
	import type { Snippet } from 'svelte';
	import type { LayoutData } from './$types';

	interface Props {
		data: LayoutData;
		children: Snippet;
	}

	let { data, children }: Props = $props();
</script>

<DocLayout packageId="batt" manifest={data.manifest} currentTag={data.selectedTag}>
	{@render children()}
</DocLayout>
