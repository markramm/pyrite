<script lang="ts">
	import EntryCard from './EntryCard.svelte';
	import { entryStore } from '$lib/stores/entries.svelte';

	interface Props {
		kb?: string;
	}

	let { kb }: Props = $props();

	const totalPages = $derived(Math.ceil(entryStore.total / entryStore.limit));
	const currentPage = $derived(Math.floor(entryStore.offset / entryStore.limit) + 1);

	function goToPage(page: number) {
		const offset = (page - 1) * entryStore.limit;
		entryStore.loadList({ kb, offset });
	}
</script>

{#if entryStore.loading}
	<div class="flex items-center justify-center py-12">
		<span class="text-zinc-400">Loading entries...</span>
	</div>
{:else if entryStore.error}
	<div class="py-12 text-center text-red-500">{entryStore.error}</div>
{:else if entryStore.entries.length === 0}
	<div class="py-12 text-center text-zinc-400">No entries found</div>
{:else}
	<div class="space-y-2">
		{#each entryStore.entries as entry (entry.id)}
			<EntryCard {entry} />
		{/each}
	</div>

	<!-- Pagination -->
	{#if totalPages > 1}
		<div class="mt-4 flex items-center justify-between">
			<span class="text-sm text-zinc-500">
				{entryStore.total} entries, page {currentPage} of {totalPages}
			</span>
			<div class="flex gap-1">
				<button
					onclick={() => goToPage(currentPage - 1)}
					disabled={currentPage <= 1}
					class="rounded border px-3 py-1 text-sm disabled:opacity-30 dark:border-zinc-700"
				>
					Prev
				</button>
				<button
					onclick={() => goToPage(currentPage + 1)}
					disabled={currentPage >= totalPages}
					class="rounded border px-3 py-1 text-sm disabled:opacity-30 dark:border-zinc-700"
				>
					Next
				</button>
			</div>
		</div>
	{/if}
{/if}
