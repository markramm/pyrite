<script lang="ts">
	import GraphView from './GraphView.svelte';
	import { api } from '$lib/api/client';
	import { onMount } from 'svelte';
	import type { GraphNode, GraphEdge } from '$lib/api/types';

	interface Props {
		entryId: string;
		kbName: string;
	}

	let { entryId, kbName }: Props = $props();

	let nodes = $state<GraphNode[]>([]);
	let edges = $state<GraphEdge[]>([]);
	let loading = $state(true);

	async function load() {
		loading = true;
		try {
			const res = await api.getGraph({
				center: entryId,
				center_kb: kbName,
				depth: 1,
				limit: 50
			});
			nodes = res.nodes;
			edges = res.edges;
		} catch {
			// Silently fail for local graph
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		load();
	});

	$effect(() => {
		// Reload when entry changes
		entryId;
		kbName;
		load();
	});
</script>

<div class="flex h-full flex-col">
	<div class="border-b border-zinc-200 px-3 py-2 dark:border-zinc-800">
		<h3 class="text-xs font-semibold uppercase text-zinc-500">Local Graph</h3>
	</div>
	<div class="flex-1">
		{#if loading}
			<div class="flex h-full items-center justify-center text-xs text-zinc-400">Loading...</div>
		{:else if nodes.length <= 1}
			<div class="flex h-full items-center justify-center p-4 text-xs text-zinc-400">
				No linked entries
			</div>
		{:else}
			<GraphView {nodes} {edges} centerId={entryId} compact />
		{/if}
	</div>
</div>
