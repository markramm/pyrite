<script lang="ts">
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { api } from '$lib/api/client';
	import { onMount } from 'svelte';
	import type { StatsResponse } from '$lib/api/types';

	let stats = $state<StatsResponse | null>(null);

	onMount(async () => {
		try {
			stats = await api.getStats();
		} catch {
			// may fail on empty index
		}
	});
</script>

<svelte:head>
	<title>Pyrite</title>
</svelte:head>

<div class="flex flex-1 flex-col overflow-y-auto">
	<!-- Hero -->
	<div class="border-b border-zinc-200 bg-zinc-50 px-6 py-10 dark:border-zinc-800 dark:bg-zinc-900">
		<div class="mx-auto max-w-4xl">
			<div class="flex items-center gap-3 mb-3">
				<div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-gold-400 to-gold-600">
					<span class="text-lg font-bold text-zinc-900">Py</span>
				</div>
				<h1 class="text-3xl font-bold text-zinc-900 dark:text-zinc-100">Pyrite</h1>
			</div>
			<p class="text-zinc-500 max-w-xl">
				Knowledge-as-Code for humans and AI agents. Browse the knowledge bases below, or
				<a href="/overview" class="text-gold-500 hover:underline">open the app</a> to search, edit, and explore.
			</p>
			{#if stats}
				<div class="mt-4 flex gap-6 text-sm text-zinc-500">
					<span><strong class="text-zinc-900 dark:text-zinc-100">{kbStore.kbs.length}</strong> knowledge bases</span>
					<span><strong class="text-zinc-900 dark:text-zinc-100">{stats.total_entries}</strong> entries</span>
					<span><strong class="text-zinc-900 dark:text-zinc-100">{stats.total_links}</strong> links</span>
				</div>
			{/if}
		</div>
	</div>

	<!-- KB Grid -->
	<div class="flex-1 px-6 py-8">
		<div class="mx-auto max-w-4xl">
			{#if kbStore.kbs.length === 0}
				<p class="text-zinc-500">No knowledge bases available.</p>
			{:else}
				<div class="grid gap-4 sm:grid-cols-2">
					{#each kbStore.kbs as kb}
						<div class="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-700 dark:bg-zinc-800">
							<h2 class="mb-1 text-lg font-semibold text-zinc-900 dark:text-zinc-100">{kb.name}</h2>
							{#if kb.description}
								<p class="mb-3 text-sm text-zinc-500">{kb.description}</p>
							{/if}
							<div class="mb-3 text-xs text-zinc-400">
								{kb.entries ?? 0} entries
								{#if kb.type !== 'generic'}<span class="mx-1">·</span> {kb.type}{/if}
							</div>
							<div class="flex gap-2">
								<a
									href="/site/{kb.name}"
									class="rounded-md bg-zinc-100 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-zinc-200 dark:bg-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-600"
								>
									Read
								</a>
								<a
									href="/orient?kb={kb.name}"
									class="rounded-md border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-500 transition-colors hover:border-zinc-400 hover:text-zinc-700 dark:border-zinc-600 dark:hover:border-zinc-500"
								>
									Explore in app
								</a>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>
