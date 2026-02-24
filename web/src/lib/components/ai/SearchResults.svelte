<script lang="ts">
	import type { SearchResult } from '$lib/api/types';

	interface Props {
		results: SearchResult[];
		loading?: boolean;
		compact?: boolean;
		onSelect?: (entry: SearchResult) => void;
	}

	let { results, loading = false, compact = false, onSelect }: Props = $props();

	const typeColors: Record<string, string> = {
		note: 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300',
		event: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
		person: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
		concept: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
		project: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
	};

	function getTypeColor(type: string): string {
		return typeColors[type] ?? typeColors.note;
	}
</script>

{#if loading}
	<div class="flex items-center justify-center py-4">
		<span class="text-sm text-zinc-400 animate-pulse">Searching...</span>
	</div>
{:else if results.length === 0}
	<p class="py-4 text-center text-sm text-zinc-400">No results</p>
{:else}
	<div class="space-y-{compact ? '1' : '2'}">
		{#each results as result}
			{#if onSelect}
				<button
					onclick={() => onSelect(result)}
					class="block w-full text-left rounded border border-zinc-200 {compact ? 'px-2 py-1.5' : 'px-3 py-2'} hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
				>
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
							{result.title}
						</span>
						<span class="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium {getTypeColor(result.entry_type)}">
							{result.entry_type}
						</span>
						{#if !compact}
							<span class="ml-auto text-[10px] text-zinc-400">{result.kb_name}</span>
						{/if}
					</div>
					{#if result.snippet && !compact}
						<p class="mt-1 text-xs text-zinc-500 line-clamp-2">{result.snippet}</p>
					{/if}
				</button>
			{:else}
				<a
					href="/entries/{result.id}"
					class="block rounded border border-zinc-200 {compact ? 'px-2 py-1.5' : 'px-3 py-2'} hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
				>
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
							{result.title}
						</span>
						<span class="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium {getTypeColor(result.entry_type)}">
							{result.entry_type}
						</span>
						{#if !compact}
							<span class="ml-auto text-[10px] text-zinc-400">{result.kb_name}</span>
						{/if}
					</div>
					{#if result.snippet && !compact}
						<p class="mt-1 text-xs text-zinc-500 line-clamp-2">{result.snippet}</p>
					{/if}
				</a>
			{/if}
		{/each}
	</div>
{/if}
