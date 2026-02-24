<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import { api } from '$lib/api/client';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { onMount } from 'svelte';
	import type { WantedPage } from '$lib/api/types';

	let pages = $state<WantedPage[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			const kb = kbStore.activeKB ?? undefined;
			const res = await api.getWantedPages(kb);
			pages = res.pages;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load wanted pages';
		} finally {
			loading = false;
		}
	});
</script>

<Topbar breadcrumbs={[{ label: 'Entries', href: '/entries' }, { label: 'Wanted Pages' }]} />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mb-4">
		<h1 class="text-2xl font-bold">Wanted Pages</h1>
		<p class="mt-1 text-sm text-zinc-500">
			Entries that are linked to but don't exist yet. Create them to fill gaps in your knowledge base.
		</p>
	</div>

	{#if loading}
		<p class="text-zinc-400">Loading...</p>
	{:else if error}
		<p class="text-red-500">{error}</p>
	{:else if pages.length === 0}
		<div class="rounded-lg border border-zinc-200 p-8 text-center dark:border-zinc-700">
			<p class="text-zinc-500">No wanted pages found. All wikilink targets resolve to existing entries.</p>
		</div>
	{:else}
		<div class="space-y-2">
			{#each pages as page}
				<div
					class="flex items-center justify-between rounded-lg border border-dashed border-red-300 p-4 dark:border-red-700"
				>
					<div>
						<span class="font-mono text-sm font-medium text-red-600 dark:text-red-400">
							{page.target_id}
						</span>
						<span class="ml-2 text-xs text-zinc-500">
							in {page.target_kb}
						</span>
						<div class="mt-1 text-xs text-zinc-400">
							Referenced by:
							{#each page.referenced_by as ref, i}
								<a
									href="/entries/{encodeURIComponent(ref)}"
									class="text-blue-600 hover:underline dark:text-blue-400"
								>{ref}</a>{#if i < page.referenced_by.length - 1},&nbsp;{/if}
							{/each}
						</div>
					</div>
					<div class="flex items-center gap-3">
						<span
							class="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800 dark:bg-red-900/30 dark:text-red-300"
						>
							{page.ref_count} {page.ref_count === 1 ? 'reference' : 'references'}
						</span>
						<a
							href="/entries/new?id={encodeURIComponent(page.target_id)}&kb={encodeURIComponent(page.target_kb)}"
							class="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
						>
							Create
						</a>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
