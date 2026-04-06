<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import TagTree from '$lib/components/common/TagTree.svelte';
	import SkeletonLoader from '$lib/components/common/SkeletonLoader.svelte';
	import { api } from '$lib/api/client';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import type { TagTreeNode } from '$lib/api/types';

	let tree = $state<TagTreeNode[]>([]);
	let flatTags = $state<{ name: string; count: number }[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let viewMode = $state<'tree' | 'flat'>('tree');
	let search = $state('');

	const selectedKb = $derived(kbStore.selectedKb?.name ?? '');

	const filteredFlat = $derived(
		search
			? flatTags.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()))
			: flatTags
	);

	async function loadTags() {
		loading = true;
		error = null;
		try {
			const [treeRes, flatRes] = await Promise.all([
				api.getTagTree(selectedKb || undefined),
				api.getTags(selectedKb || undefined),
			]);
			tree = treeRes.tree;
			flatTags = flatRes.tags;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load tags';
		} finally {
			loading = false;
		}
	}

	function selectTag(tag: string) {
		goto(`/entries?tag=${encodeURIComponent(tag)}`);
	}

	onMount(loadTags);

	$effect(() => {
		// Reload when KB selection changes
		selectedKb;
		loadTags();
	});
</script>

<svelte:head><title>Tags — Pyrite</title></svelte:head>

<Topbar breadcrumbs={[{ label: 'Tags' }]} />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mx-auto max-w-3xl">
		<div class="mb-6 flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-bold text-zinc-100">Tags</h1>
				<p class="mt-1 text-sm text-zinc-500">{flatTags.length} tags across {selectedKb || 'all KBs'}</p>
			</div>
			<div class="flex gap-2">
				<button
					onclick={() => (viewMode = 'tree')}
					class="rounded-md px-3 py-1.5 text-sm font-medium {viewMode === 'tree'
						? 'bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/30'
						: 'text-zinc-400 hover:text-zinc-300'}"
				>
					Tree
				</button>
				<button
					onclick={() => (viewMode = 'flat')}
					class="rounded-md px-3 py-1.5 text-sm font-medium {viewMode === 'flat'
						? 'bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/30'
						: 'text-zinc-400 hover:text-zinc-300'}"
				>
					Flat
				</button>
			</div>
		</div>

		{#if viewMode === 'flat'}
			<input
				type="text"
				placeholder="Filter tags..."
				bind:value={search}
				class="mb-4 w-full rounded-lg border border-zinc-700 bg-zinc-800/80 px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 outline-none focus:ring-1 focus:ring-amber-500/40"
			/>
		{/if}

		{#if loading}
			<SkeletonLoader lines={8} />
		{:else if error}
			<div class="rounded-lg border border-red-800 bg-red-900/20 p-4 text-sm text-red-400">
				{error}
			</div>
		{:else if viewMode === 'tree'}
			{#if tree.length > 0}
				<div class="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
					<TagTree nodes={tree} onSelect={selectTag} />
				</div>
			{:else}
				<p class="py-8 text-center text-zinc-500">No hierarchical tags found.</p>
			{/if}
		{:else}
			<div class="grid gap-1">
				{#each filteredFlat as tag (tag.name)}
					<button
						onclick={() => selectTag(tag.name)}
						class="flex items-center justify-between rounded-md px-3 py-1.5 text-left text-sm hover:bg-zinc-800"
					>
						<span class="text-zinc-300">{tag.name}</span>
						<span class="text-xs text-zinc-600">{tag.count}</span>
					</button>
				{:else}
					<p class="py-8 text-center text-zinc-500">
						{search ? `No tags matching "${search}"` : 'No tags found.'}
					</p>
				{/each}
			</div>
		{/if}
	</div>
</div>
