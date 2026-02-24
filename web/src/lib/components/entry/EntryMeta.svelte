<script lang="ts">
	import TagBadge from '$lib/components/common/TagBadge.svelte';
	import type { EntryResponse } from '$lib/api/types';

	interface Props {
		entry: EntryResponse;
	}

	let { entry }: Props = $props();
</script>

<div class="space-y-3 text-sm">
	<div>
		<span class="text-zinc-500">Type:</span>
		<span class="ml-2 rounded bg-zinc-100 px-1.5 py-0.5 text-xs dark:bg-zinc-800">{entry.entry_type}</span>
	</div>
	<div>
		<span class="text-zinc-500">KB:</span>
		<span class="ml-2">{entry.kb_name}</span>
	</div>
	{#if entry.date}
		<div>
			<span class="text-zinc-500">Date:</span>
			<span class="ml-2">{entry.date}</span>
		</div>
	{/if}
	{#if entry.importance}
		<div>
			<span class="text-zinc-500">Importance:</span>
			<span class="ml-2">{entry.importance}/10</span>
		</div>
	{/if}
	{#if entry.tags.length > 0}
		<div>
			<span class="text-zinc-500">Tags:</span>
			<div class="mt-1 flex flex-wrap gap-1">
				{#each entry.tags as tag}
					<TagBadge {tag} href="/entries?tag={encodeURIComponent(tag)}" />
				{/each}
			</div>
		</div>
	{/if}
	{#if entry.participants.length > 0}
		<div>
			<span class="text-zinc-500">Participants:</span>
			<div class="mt-1 space-y-0.5">
				{#each entry.participants as p}
					<div class="text-xs">{p}</div>
				{/each}
			</div>
		</div>
	{/if}
	<div class="text-xs text-zinc-400">
		<div>ID: {entry.id}</div>
		<div>File: {entry.file_path}</div>
		{#if entry.created_at}
			<div>Created: {new Date(entry.created_at).toLocaleString()}</div>
		{/if}
		{#if entry.updated_at}
			<div>Updated: {new Date(entry.updated_at).toLocaleString()}</div>
		{/if}
	</div>
</div>
