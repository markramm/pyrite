<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import { collectionStore } from '$lib/stores/collections.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { onMount } from 'svelte';
	import ErrorState from '$lib/components/common/ErrorState.svelte';
	import EmptyState from '$lib/components/common/EmptyState.svelte';

	onMount(() => {
		const kb = kbStore.activeKB ?? undefined;
		collectionStore.loadCollections(kb);
	});

	$effect(() => {
		const kb = kbStore.activeKB ?? undefined;
		if (kb) {
			collectionStore.loadCollections(kb);
		}
	});
</script>

<Topbar breadcrumbs={[{ label: 'Collections' }]} />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mb-4 flex items-center justify-between">
		<h1 class="text-2xl font-bold">Collections</h1>
		<a
			href="/collections/new"
			class="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
		>
			New Virtual Collection
		</a>
	</div>

	{#if collectionStore.loading}
		<div class="flex items-center justify-center py-12">
			<div class="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-blue-600"></div>
		</div>
	{:else if collectionStore.error}
		<ErrorState message={collectionStore.error} onretry={() => collectionStore.loadCollections(kbStore.activeKB ?? undefined)} />
	{:else if collectionStore.collections.length === 0}
		<EmptyState
			icon="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
			title="No collections found"
			description="Add a __collection.yaml file to any folder in your KB, or create a virtual collection."
			actionLabel="New Virtual Collection"
			actionHref="/collections/new"
		/>
	{:else}
		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each collectionStore.collections as collection}
				<a
					href="/collections/{collection.id}?kb={encodeURIComponent(collection.kb_name)}"
					class="rounded-lg border border-zinc-200 p-5 transition-colors hover:border-zinc-400 dark:border-zinc-700 dark:hover:border-zinc-500"
				>
					<div class="mb-2 flex items-center gap-2">
						{#if collection.icon}
							<span class="text-lg">{collection.icon}</span>
						{:else}
							<svg class="h-5 w-5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
							</svg>
						{/if}
						<h3 class="font-medium">{collection.title}</h3>
						{#if collection.source_type === 'query'}
							<span class="rounded bg-purple-100 px-1.5 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">Virtual</span>
						{/if}
					</div>
					{#if collection.description}
						<p class="mb-3 line-clamp-2 text-sm text-zinc-400">{collection.description}</p>
					{/if}
					<div class="flex items-center justify-between text-xs text-zinc-400">
						{#if collection.source_type === 'query' && collection.query}
							<span class="truncate font-mono">{collection.query}</span>
						{:else}
							<span>{collection.folder_path}</span>
						{/if}
						<span class="ml-2 shrink-0 rounded bg-zinc-100 px-1.5 py-0.5 dark:bg-zinc-800">{collection.kb_name}</span>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>
