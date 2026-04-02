<script lang="ts">
	import EntryCard from './EntryCard.svelte';
	import { entryStore } from '$lib/stores/entries.svelte';
	import ErrorState from '$lib/components/common/ErrorState.svelte';
	import EmptyState from '$lib/components/common/EmptyState.svelte';
	import SkeletonLoader from '$lib/components/common/SkeletonLoader.svelte';

	interface Props {
		kb?: string;
		participantFilter?: string;
	}

	let { kb, participantFilter = '' }: Props = $props();

	// Client-side participant filtering (participants live in metadata, not a DB column)
	const filteredEntries = $derived(
		participantFilter
			? entryStore.entries.filter((entry) =>
					entry.participants?.some((p) => p.toLowerCase().includes(participantFilter))
				)
			: entryStore.entries
	);

	const displayTotal = $derived(participantFilter ? filteredEntries.length : entryStore.total);
	const totalPages = $derived(Math.ceil(entryStore.total / entryStore.limit));
	const currentPage = $derived(Math.floor(entryStore.offset / entryStore.limit) + 1);

	function goToPage(page: number) {
		const offset = (page - 1) * entryStore.limit;
		entryStore.loadList({ kb, offset });
	}
</script>

{#if entryStore.loading}
	<SkeletonLoader variant="cards" lines={5} />
{:else if entryStore.error}
	<ErrorState message={entryStore.error} onretry={() => entryStore.loadList({ kb })} />
{:else if filteredEntries.length === 0}
	<EmptyState
		icon="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
		title="No entries found"
		description={participantFilter
			? `No entries match participant "${participantFilter}".`
			: 'Create your first entry to start building your knowledge base.'}
		actionLabel={participantFilter ? undefined : 'New Entry'}
		actionHref={participantFilter ? undefined : '/entries/new'}
	/>
{:else}
	<div class="mb-2 text-sm text-zinc-500">
		{displayTotal} {displayTotal === 1 ? 'entry' : 'entries'}
		{#if participantFilter}
			<span class="text-zinc-400">(filtered from {entryStore.total} total)</span>
		{/if}
	</div>

	<div class="space-y-3">
		{#each filteredEntries as entry (entry.id)}
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
