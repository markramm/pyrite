<script lang="ts">
	import EntryCard from './EntryCard.svelte';
	import { entryStore } from '$lib/stores/entries.svelte';
	import ErrorState from '$lib/components/common/ErrorState.svelte';
	import EmptyState from '$lib/components/common/EmptyState.svelte';

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
	<ErrorState message={entryStore.error} onretry={() => entryStore.loadList({ kb })} />
{:else if entryStore.entries.length === 0}
	<EmptyState
		icon="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
		title="No entries found"
		description="Create your first entry to start building your knowledge base."
		actionLabel="New Entry"
		actionHref="/entries/new"
	/>
{:else}
	<div class="mb-2 text-sm text-zinc-500">
		{entryStore.total} {entryStore.total === 1 ? 'entry' : 'entries'}
	</div>

	<div class="space-y-3">
		{#each entryStore.entries as entry (entry.id)}
			<EntryCard {entry} />
		{/each}
	</div>

	<!-- Pagination -->
	{#if totalPages > 1}
		<div class="mt-4 flex items-center justify-between">
			<span class="text-sm text-zinc-500">
				Page {currentPage} of {totalPages}
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
