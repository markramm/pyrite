<script lang="ts">
	import TagBadge from '$lib/components/common/TagBadge.svelte';
	import type { EntryResponse } from '$lib/api/types';
	import { goto } from '$app/navigation';
	import { typeColor } from '$lib/constants';

	interface Props {
		entry: EntryResponse;
	}

	let { entry }: Props = $props();

	const borderColor = $derived(typeColor(entry.entry_type));

	function onTagClick(tag: string) {
		return (e: MouseEvent) => {
			e.preventDefault();
			e.stopPropagation();
			goto(`/entries?tag=${encodeURIComponent(tag)}`);
		};
	}
</script>

<a
	href="/entries/{entry.id}"
	class="block rounded-lg border border-zinc-200 p-5 transition-colors hover:border-zinc-400 dark:border-zinc-700 dark:hover:border-zinc-500"
	style="border-left: 3px solid {borderColor}"
>
	<div class="mb-1 flex items-center justify-between">
		<h3 class="font-medium">{entry.title}</h3>
		<span class="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-500 dark:bg-zinc-800">
			{entry.entry_type}
		</span>
	</div>

	{#if entry.summary}
		<p class="mb-2 line-clamp-2 text-sm text-zinc-400 dark:text-zinc-400">{entry.summary}</p>
	{:else if entry.body}
		<p class="mb-2 line-clamp-2 text-sm text-zinc-400 dark:text-zinc-400">{entry.body.slice(0, 150)}</p>
	{/if}

	<div class="flex items-center justify-between">
		<div class="flex flex-wrap gap-1">
			{#each entry.tags.slice(0, 3) as tag}
				<TagBadge {tag} onclick={onTagClick(tag)} />
			{/each}
			{#if entry.tags.length > 3}
				<span class="text-xs text-zinc-400">+{entry.tags.length - 3}</span>
			{/if}
		</div>
		<span class="text-xs text-zinc-400">{entry.kb_name}</span>
	</div>
</a>
