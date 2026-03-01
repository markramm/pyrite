<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import EntryList from '$lib/components/entry/EntryList.svelte';
	import { entryStore } from '$lib/stores/entries.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { searchStore } from '$lib/stores/search.svelte';
	import { api } from '$lib/api/client';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	let filterType = $state('');
	let entryTypes = $state<string[]>([]);

	// Get params from URL
	const urlKB = $derived($page.url.searchParams.get('kb') ?? undefined);
	const urlTag = $derived($page.url.searchParams.get('tag') ?? undefined);

	onMount(async () => {
		// Read initial filter from URL
		filterType = $page.url.searchParams.get('type') ?? '';

		loadEntries();

		// Load dynamic types
		try {
			const kb = urlKB ?? kbStore.activeKB ?? undefined;
			const res = await api.getEntryTypes(kb);
			entryTypes = res.types;
		} catch {
			// Fall back to empty — dropdown will just show "All types"
		}
	});

	function loadEntries() {
		const kb = urlKB ?? kbStore.activeKB ?? undefined;
		entryStore.loadList({
			kb,
			entry_type: filterType || undefined,
			tag: urlTag,
		});
	}

	// Reload when KB or tag changes
	$effect(() => {
		const kb = urlKB ?? kbStore.activeKB ?? undefined;
		const tag = urlTag;
		if (kb || tag) {
			entryStore.loadList({
				kb,
				entry_type: filterType || undefined,
				tag,
			});
		}
	});

	function onFilterChange() {
		loadEntries();
	}

	function onSortChange(e: Event) {
		const value = (e.target as HTMLSelectElement).value;
		entryStore.sortBy = value;
		loadEntries();
	}

	function toggleSortOrder() {
		entryStore.sortOrder = entryStore.sortOrder === 'desc' ? 'asc' : 'desc';
		loadEntries();
	}

	function clearTag() {
		goto('/entries');
	}
</script>

<Topbar breadcrumbs={[{ label: 'Entries' }]} />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mb-4 flex flex-wrap items-center justify-between gap-2">
		<h1 class="text-2xl font-bold">Entries</h1>
		<div class="flex flex-wrap items-center gap-3">
			<!-- Sort -->
			<select
				value={entryStore.sortBy}
				onchange={onSortChange}
				class="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800"
			>
				<option value="updated_at">Updated</option>
				<option value="created_at">Created</option>
				<option value="title">Title</option>
				<option value="entry_type">Type</option>
			</select>
			<button
				onclick={toggleSortOrder}
				class="rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700"
				title="Toggle sort direction"
				aria-label="Toggle sort direction"
			>
				{entryStore.sortOrder === 'desc' ? '↓' : '↑'}
			</button>

			<!-- Type filter -->
			<select
				bind:value={filterType}
				onchange={onFilterChange}
				class="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800"
			>
				<option value="">All types</option>
				{#each entryTypes as t}
					<option value={t}>{t}</option>
				{/each}
			</select>

			<!-- Search -->
			<input
				type="search"
				placeholder="Search..."
				value={searchStore.query}
				oninput={(e) => searchStore.setQuery(e.currentTarget.value)}
				class="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800"
			/>

			<!-- New entry -->
			<a
				href="/entries/new"
				class="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
			>
				New Entry
			</a>
		</div>
	</div>

	<!-- Active tag filter -->
	{#if urlTag}
		<div class="mb-3 flex items-center gap-2">
			<span class="text-sm text-zinc-500">Filtered by tag:</span>
			<span class="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
				{urlTag}
				<button onclick={clearTag} class="ml-0.5 hover:text-blue-600 dark:hover:text-blue-100">&times;</button>
			</span>
		</div>
	{/if}

	<!-- Search results or entry list -->
	{#if searchStore.query && searchStore.results.length > 0}
		<div class="mb-4 text-sm text-zinc-500">
			{searchStore.results.length} search results for "{searchStore.query}"
		</div>
		<div class="space-y-2">
			{#each searchStore.results as result}
				<a
					href="/entries/{result.id}"
					class="block rounded-lg border border-zinc-200 p-3 hover:border-zinc-400 dark:border-zinc-700"
				>
					<div class="flex items-center justify-between">
						<span class="font-medium">{result.title}</span>
						<span class="text-xs text-zinc-500">{result.entry_type}</span>
					</div>
					{#if result.snippet}
						<p class="mt-1 text-sm text-zinc-400">{result.snippet}</p>
					{/if}
				</a>
			{/each}
		</div>
	{:else}
		<EntryList kb={urlKB ?? kbStore.activeKB ?? undefined} />
	{/if}
</div>
