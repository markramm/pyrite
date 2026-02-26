<script lang="ts">
	import TagBadge from '$lib/components/common/TagBadge.svelte';
	import type { EntryResponse } from '$lib/api/types';
	import { goto } from '$app/navigation';

	interface Props {
		entries: EntryResponse[];
		cardFields?: string[];
	}

	let { entries, cardFields = ['title', 'body', 'entry_type', 'date', 'tags'] }: Props = $props();

	function getExcerpt(body?: string, maxLen = 120): string {
		if (!body) return '';
		const plain = body.replace(/[#*_\[\]`]/g, '').trim();
		return plain.length > maxLen ? plain.slice(0, maxLen) + '...' : plain;
	}

	const typeColors: Record<string, string> = {
		event: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
		person: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
		organization: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
		note: 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300',
		topic: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
	};

	function formatDate(dateStr?: string): string {
		if (!dateStr) return '';
		try {
			return new Date(dateStr).toLocaleDateString(undefined, {
				year: 'numeric',
				month: 'short',
				day: 'numeric'
			});
		} catch {
			return dateStr;
		}
	}
</script>

<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
	{#each entries as entry (entry.id)}
		<button
			onclick={() => goto(`/entries/${entry.id}?kb=${entry.kb_name}`)}
			class="group flex w-full cursor-pointer flex-col rounded-lg border border-zinc-200 bg-white p-4 text-left transition-shadow hover:shadow-lg dark:border-zinc-700 dark:bg-zinc-800"
		>
			<!-- Title -->
			{#if cardFields.includes('title')}
				<h3 class="text-base font-semibold text-zinc-900 group-hover:text-blue-600 dark:text-zinc-100 dark:group-hover:text-blue-400">
					{entry.title}
				</h3>
			{/if}

			<!-- Excerpt -->
			{#if cardFields.includes('body') && entry.body}
				<p class="mt-1.5 line-clamp-3 text-sm text-zinc-500 dark:text-zinc-400">
					{getExcerpt(entry.summary ?? entry.body)}
				</p>
			{/if}

			<!-- Footer: type, date, tags -->
			<div class="mt-auto flex flex-col gap-2 pt-3">
				<div class="flex items-center gap-2">
					{#if cardFields.includes('entry_type')}
						<span class="rounded-full px-2 py-0.5 text-xs font-medium {typeColors[entry.entry_type] ?? 'bg-zinc-100 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-400'}">
							{entry.entry_type}
						</span>
					{/if}
					{#if cardFields.includes('date') && (entry.date || entry.updated_at)}
						<span class="text-xs text-zinc-400 dark:text-zinc-500">
							{formatDate(entry.date ?? entry.updated_at)}
						</span>
					{/if}
				</div>
				{#if cardFields.includes('tags') && entry.tags.length > 0}
					<div class="flex flex-wrap gap-1">
						{#each entry.tags.slice(0, 3) as tag}
							<TagBadge {tag} />
						{/each}
						{#if entry.tags.length > 3}
							<span class="text-xs text-zinc-400">+{entry.tags.length - 3}</span>
						{/if}
					</div>
				{/if}
			</div>
		</button>
	{/each}
</div>

{#if entries.length === 0}
	<div class="py-12 text-center text-zinc-400">
		No entries in this collection
	</div>
{/if}
