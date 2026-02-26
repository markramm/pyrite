<script lang="ts">
	import { api } from '$lib/api/client';
	import type { EntryResponse } from '$lib/api/types';

	interface Props {
		initialQuery?: string;
		kb?: string;
		onQueryChange?: (query: string) => void;
	}

	let { initialQuery = '', kb, onQueryChange }: Props = $props();

	let query = $state(initialQuery);
	let previewEntries = $state<EntryResponse[]>([]);
	let previewTotal = $state(0);
	let previewParsed = $state<Record<string, unknown>>({});
	let previewLoading = $state(false);
	let previewError = $state<string | null>(null);
	let debounceTimer: ReturnType<typeof setTimeout> | undefined;

	const operators = [
		{ label: 'type:', example: 'type:note' },
		{ label: 'tags:', example: 'tags:core,api' },
		{ label: 'status:', example: 'status:proposed' },
		{ label: 'date_from:', example: 'date_from:2024-01-01' },
		{ label: 'date_to:', example: 'date_to:2024-12-31' },
		{ label: 'kb:', example: 'kb:pyrite' },
		{ label: 'sort:', example: 'sort:updated_at' },
		{ label: 'limit:', example: 'limit:50' }
	];

	function appendOperator(example: string) {
		query = query ? `${query} ${example}` : example;
		schedulePreview();
	}

	function schedulePreview() {
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(runPreview, 500);
	}

	async function runPreview() {
		if (!query.trim()) {
			previewEntries = [];
			previewTotal = 0;
			previewParsed = {};
			previewError = null;
			return;
		}
		previewLoading = true;
		previewError = null;
		try {
			const res = await api.previewCollectionQuery(query, kb, 10);
			previewEntries = res.entries;
			previewTotal = res.total;
			previewParsed = res.query_parsed;
		} catch (e) {
			previewError = e instanceof Error ? e.message : 'Preview failed';
		} finally {
			previewLoading = false;
		}
		onQueryChange?.(query);
	}

	function handleInput() {
		schedulePreview();
		onQueryChange?.(query);
	}
</script>

<div class="space-y-4">
	<!-- Query input -->
	<div>
		<input
			type="text"
			bind:value={query}
			oninput={handleInput}
			placeholder="e.g. type:backlog_item status:proposed tags:core"
			class="w-full rounded-md border border-zinc-300 px-3 py-2 font-mono text-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
		/>
	</div>

	<!-- Operator chips -->
	<div class="flex flex-wrap gap-2">
		{#each operators as op}
			<button
				type="button"
				onclick={() => appendOperator(op.example)}
				class="rounded-full border border-zinc-300 px-2.5 py-1 text-xs text-zinc-600 transition-colors hover:border-blue-400 hover:text-blue-600 dark:border-zinc-600 dark:text-zinc-400 dark:hover:border-blue-500 dark:hover:text-blue-400"
				title="Add {op.example}"
			>
				{op.label}
			</button>
		{/each}
		<button
			type="button"
			onclick={runPreview}
			class="rounded-full bg-blue-600 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-blue-700"
		>
			Preview
		</button>
	</div>

	<!-- Preview panel -->
	<div class="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-900">
		{#if previewLoading}
			<div class="flex items-center gap-2 text-sm text-zinc-400">
				<div
					class="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-blue-600"
				></div>
				Loading preview...
			</div>
		{:else if previewError}
			<div class="text-sm text-red-600 dark:text-red-400">
				{previewError}
			</div>
		{:else if !query.trim()}
			<p class="text-sm text-zinc-400">
				Enter a query above to preview matching entries.
			</p>
		{:else}
			<div class="space-y-3">
				<!-- Result count -->
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium text-zinc-600 dark:text-zinc-300">
						{previewTotal} matching {previewTotal === 1 ? 'entry' : 'entries'}
					</span>
				</div>

				<!-- Parsed query -->
				{#if Object.keys(previewParsed).length > 0}
					<div class="flex flex-wrap gap-1.5">
						{#each Object.entries(previewParsed) as [key, value]}
							<span
								class="rounded bg-zinc-200 px-1.5 py-0.5 text-xs text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300"
							>
								{key}: {typeof value === 'object' ? JSON.stringify(value) : value}
							</span>
						{/each}
					</div>
				{/if}

				<!-- Entry list -->
				{#if previewEntries.length > 0}
					<ul class="space-y-1">
						{#each previewEntries as entry}
							<li
								class="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-300"
							>
								<span
									class="inline-block rounded bg-zinc-200 px-1 py-0.5 text-xs dark:bg-zinc-700"
									>{entry.entry_type}</span
								>
								<span class="truncate">{entry.title}</span>
							</li>
						{/each}
					</ul>
					{#if previewTotal > previewEntries.length}
						<p class="text-xs text-zinc-400">
							...and {previewTotal - previewEntries.length} more
						</p>
					{/if}
				{:else}
					<p class="text-sm text-zinc-400">No entries match this query.</p>
				{/if}
			</div>
		{/if}
	</div>
</div>
