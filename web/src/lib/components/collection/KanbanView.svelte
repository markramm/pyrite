<script lang="ts">
	import type { EntryResponse } from '$lib/api/types';
	import { goto } from '$app/navigation';

	interface Props {
		entries: EntryResponse[];
		groupBy?: string;
		columnOrder?: string[];
		onFieldUpdate?: (entryId: string, field: string, value: string) => void;
	}

	let { entries, groupBy = 'status', columnOrder, onFieldUpdate }: Props = $props();

	let dragEntryId = $state<string | null>(null);
	let dragOverColumn = $state<string | null>(null);

	const columns = $derived.by(() => {
		const groups = new Map<string, EntryResponse[]>();

		for (const entry of entries) {
			const value = (entry as Record<string, unknown>)[groupBy] as string ?? '';
			const key = value || 'Ungrouped';
			if (!groups.has(key)) groups.set(key, []);
			groups.get(key)!.push(entry);
		}

		if (columnOrder?.length) {
			const ordered = new Map<string, EntryResponse[]>();
			for (const col of columnOrder) {
				ordered.set(col, groups.get(col) ?? []);
				groups.delete(col);
			}
			for (const [key, vals] of groups) {
				ordered.set(key, vals);
			}
			return ordered;
		}

		return groups;
	});

	const typeColors: Record<string, string> = {
		event: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
		person: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
		organization: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
		note: 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300',
		topic: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
	};

	function handleDragStart(e: DragEvent, entryId: string) {
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
			e.dataTransfer.setData('text/plain', entryId);
		}
		dragEntryId = entryId;
	}

	function handleDragOver(e: DragEvent, columnKey: string) {
		e.preventDefault();
		if (e.dataTransfer) {
			e.dataTransfer.dropEffect = 'move';
		}
		dragOverColumn = columnKey;
	}

	function handleDragLeave() {
		dragOverColumn = null;
	}

	function handleDrop(e: DragEvent, columnKey: string) {
		e.preventDefault();
		dragOverColumn = null;
		const entryId = e.dataTransfer?.getData('text/plain');
		if (entryId && onFieldUpdate && columnKey !== 'Ungrouped') {
			onFieldUpdate(entryId, groupBy, columnKey);
		}
		dragEntryId = null;
	}

	function handleDragEnd() {
		dragEntryId = null;
		dragOverColumn = null;
	}
</script>

<div class="flex gap-4 overflow-x-auto pb-4">
	{#each [...columns.entries()] as [columnKey, columnEntries]}
		<div
			class="flex min-w-[280px] max-w-[320px] flex-shrink-0 flex-col rounded-lg border border-zinc-200 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 {dragOverColumn === columnKey ? 'ring-2 ring-blue-400 dark:ring-blue-500' : ''}"
			ondragover={(e) => handleDragOver(e, columnKey)}
			ondragleave={handleDragLeave}
			ondrop={(e) => handleDrop(e, columnKey)}
			role="group"
			aria-label="Kanban column: {columnKey}"
		>
			<!-- Column header -->
			<div class="flex items-center justify-between border-b border-zinc-200 px-3 py-2 dark:border-zinc-700">
				<h3 class="text-sm font-semibold text-zinc-700 dark:text-zinc-300">{columnKey}</h3>
				<span class="rounded-full bg-zinc-200 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-700 dark:text-zinc-400">
					{columnEntries.length}
				</span>
			</div>

			<!-- Cards -->
			<div class="flex flex-1 flex-col gap-2 p-2">
				{#each columnEntries as entry (entry.id)}
					<button
						draggable="true"
						ondragstart={(e) => handleDragStart(e, entry.id)}
						ondragend={handleDragEnd}
						onclick={() => goto(`/entries/${entry.id}?kb=${entry.kb_name}`)}
						class="w-full cursor-pointer rounded-md border border-zinc-200 bg-white p-3 text-left shadow-sm transition-shadow hover:shadow-md dark:border-zinc-600 dark:bg-zinc-800 {dragEntryId === entry.id ? 'opacity-50' : ''}"
					>
						<p class="text-sm font-medium text-zinc-900 dark:text-zinc-100">{entry.title}</p>
						<div class="mt-2 flex flex-wrap items-center gap-1.5">
							<span class="rounded-full px-1.5 py-0.5 text-xs font-medium {typeColors[entry.entry_type] ?? 'bg-zinc-100 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-400'}">
								{entry.entry_type}
							</span>
							{#each entry.tags.slice(0, 2) as tag}
								<span class="inline-flex items-center rounded-full bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
									{tag}
								</span>
							{/each}
						</div>
					</button>
				{/each}
				{#if columnEntries.length === 0}
					<div class="py-6 text-center text-xs text-zinc-400">No entries</div>
				{/if}
			</div>
		</div>
	{/each}
	{#if columns.size === 0}
		<div class="w-full py-12 text-center text-zinc-400">
			No entries to display. Try grouping by a different field.
		</div>
	{/if}
</div>
