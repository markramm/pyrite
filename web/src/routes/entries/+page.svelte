<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import EntryList from '$lib/components/entry/EntryList.svelte';
	import { entryStore } from '$lib/stores/entries.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { searchStore } from '$lib/stores/search.svelte';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';

	let filterType = $state('');

	// Get kb from URL query params
	const urlKB = $derived($page.url.searchParams.get('kb') ?? undefined);

	onMount(() => {
		entryStore.loadList({ kb: urlKB ?? kbStore.activeKB ?? undefined });
	});

	// Reload when KB changes
	$effect(() => {
		const kb = urlKB ?? kbStore.activeKB ?? undefined;
		if (kb) {
			entryStore.loadList({ kb, entry_type: filterType || undefined });
		}
	});

	function onFilterChange() {
		const kb = urlKB ?? kbStore.activeKB ?? undefined;
		entryStore.loadList({ kb, entry_type: filterType || undefined });
	}
</script>

<Topbar breadcrumbs={[{ label: 'Entries' }]} />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mb-4 flex items-center justify-between">
		<h1 class="text-2xl font-bold">Entries</h1>
		<div class="flex items-center gap-3">
			<!-- Type filter -->
			<select
				bind:value={filterType}
				onchange={onFilterChange}
				class="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800"
			>
				<option value="">All types</option>
				<option value="event">Events</option>
				<option value="person">People</option>
				<option value="organization">Organizations</option>
				<option value="note">Notes</option>
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
