<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { api } from '$lib/api/client';
	import { onMount } from 'svelte';
	import type { StatsResponse, TagCount } from '$lib/api/types';

	let stats = $state<StatsResponse | null>(null);
	let topTags = $state<TagCount[]>([]);

	onMount(async () => {
		try {
			stats = await api.getStats();
			const tagsRes = await api.getTags();
			topTags = tagsRes.tags.slice(0, 10);
		} catch {
			// stats may fail if index is empty
		}
	});
</script>

<Topbar title="Dashboard" />

<div class="flex-1 overflow-y-auto p-6">
	<h1 class="mb-6 text-2xl font-bold">Dashboard</h1>

	<!-- Stats Cards -->
	<div class="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
		<div class="rounded-lg border border-zinc-200 p-4 dark:border-zinc-700">
			<div class="text-sm text-zinc-500">Knowledge Bases</div>
			<div class="mt-1 text-2xl font-bold">{kbStore.kbs.length}</div>
		</div>
		<div class="rounded-lg border border-zinc-200 p-4 dark:border-zinc-700">
			<div class="text-sm text-zinc-500">Total Entries</div>
			<div class="mt-1 text-2xl font-bold">{stats?.total_entries ?? '-'}</div>
		</div>
		<div class="rounded-lg border border-zinc-200 p-4 dark:border-zinc-700">
			<div class="text-sm text-zinc-500">Tags</div>
			<div class="mt-1 text-2xl font-bold">{stats?.total_tags ?? '-'}</div>
		</div>
		<div class="rounded-lg border border-zinc-200 p-4 dark:border-zinc-700">
			<div class="text-sm text-zinc-500">Links</div>
			<div class="mt-1 text-2xl font-bold">{stats?.total_links ?? '-'}</div>
		</div>
	</div>

	<!-- KBs overview -->
	<div class="mb-8">
		<h2 class="mb-3 text-lg font-semibold">Knowledge Bases</h2>
		{#if kbStore.kbs.length === 0}
			<p class="text-zinc-400">No knowledge bases configured. Run <code>pyrite kb add</code> to get started.</p>
		{:else}
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
				{#each kbStore.kbs as kb}
					<a
						href="/entries?kb={kb.name}"
						class="rounded-lg border border-zinc-200 p-4 transition-colors hover:border-zinc-400 dark:border-zinc-700 dark:hover:border-zinc-500"
					>
						<div class="flex items-center justify-between">
							<span class="font-medium">{kb.name}</span>
							<span class="text-xs text-zinc-500">{kb.type}</span>
						</div>
						<div class="mt-1 text-sm text-zinc-400">{kb.entries} entries</div>
					</a>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Top Tags -->
	{#if topTags.length > 0}
		<div>
			<h2 class="mb-3 text-lg font-semibold">Top Tags</h2>
			<div class="flex flex-wrap gap-2">
				{#each topTags as tag}
					<span class="rounded-full bg-zinc-100 px-3 py-1 text-sm dark:bg-zinc-800">
						{tag.name}
						<span class="ml-1 text-zinc-400">({tag.count})</span>
					</span>
				{/each}
			</div>
		</div>
	{/if}
</div>
