<script lang="ts">
	import { typeColor } from '$lib/constants';
	import { api } from '$lib/api/client';
	import type { SearchResult } from '$lib/api/types';

	let query = $state('');
	let results = $state<SearchResult[]>([]);
	let loading = $state(false);
	let searched = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	function onInput(e: Event) {
		query = (e.target as HTMLInputElement).value;
		if (debounceTimer) clearTimeout(debounceTimer);
		if (!query.trim()) { results = []; searched = false; return; }
		debounceTimer = setTimeout(doSearch, 300);
	}

	async function doSearch() {
		if (!query.trim()) return;
		loading = true;
		try {
			const res = await api.search(query, { mode: 'hybrid', limit: 50 });
			results = res.results;
		} catch { results = []; }
		finally { loading = false; searched = true; }
	}
</script>

<svelte:head>
	<title>Search — Pyrite Knowledge Base</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1 class="mb-6 text-3xl font-bold text-zinc-900 dark:text-zinc-100">Search</h1>

<input type="text" value={query} oninput={onInput} onkeydown={(e) => { if (e.key === 'Enter') doSearch(); }}
	placeholder="Search across all knowledge bases..."
	class="mb-6 w-full rounded-lg border border-zinc-300 bg-white px-4 py-3 text-lg outline-none focus:border-gold-400 dark:border-zinc-700 dark:bg-zinc-800" />

{#if loading}
	<p class="text-zinc-400">Searching...</p>
{:else if searched && results.length === 0}
	<p class="text-zinc-500">No results for "{query}"</p>
{:else if results.length > 0}
	<p class="mb-4 text-sm text-zinc-500">{results.length} results</p>
	<div class="space-y-2">
		{#each results as r}
			<a href="/site/{r.kb_name}/{encodeURIComponent(r.id)}" class="block rounded-lg border border-zinc-200 bg-white px-4 py-3 transition-colors hover:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-800 dark:hover:border-zinc-500" style="border-left: 3px solid {typeColor(r.entry_type)}">
				<div class="flex items-center gap-2">
					<span class="font-medium text-zinc-900 dark:text-zinc-100">{r.title}</span>
					<span class="rounded px-1.5 py-0.5 text-xs font-medium" style="background-color: {typeColor(r.entry_type)}20; color: {typeColor(r.entry_type)}">{r.entry_type}</span>
					<span class="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-500 dark:bg-zinc-700">{r.kb_name}</span>
				</div>
				{#if r.snippet}<p class="mt-1 text-sm text-zinc-500">{r.snippet}</p>{/if}
			</a>
		{/each}
	</div>
{/if}
