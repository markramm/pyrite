<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import { api } from '$lib/api/client';
	import { onMount } from 'svelte';
	import type { TimelineEvent } from '$lib/api/types';

	let events = $state<TimelineEvent[]>([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			const res = await api.getTimeline({ limit: 100 });
			events = res.events;
		} catch {
			// timeline may be empty
		} finally {
			loading = false;
		}
	});
</script>

<Topbar title="Timeline" />
<div class="flex-1 overflow-y-auto p-6">
	<h1 class="mb-6 text-2xl font-bold">Timeline</h1>
	{#if loading}
		<p class="text-zinc-400">Loading...</p>
	{:else if events.length === 0}
		<p class="text-zinc-400">No timeline events found.</p>
	{:else}
		<div class="space-y-3">
			{#each events as event}
				<a
					href="/entries/{event.id}"
					class="flex items-center gap-4 rounded-lg border border-zinc-200 p-3 hover:border-zinc-400 dark:border-zinc-700"
				>
					<span class="w-24 shrink-0 text-sm font-mono text-zinc-500">{event.date}</span>
					<span class="flex-1 font-medium">{event.title}</span>
					<span class="text-xs text-zinc-400">imp: {event.importance}</span>
				</a>
			{/each}
		</div>
	{/if}
</div>
