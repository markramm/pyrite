<script lang="ts">
	import { typeColor } from '$lib/constants';
	import type { PageData } from './$types';
	let { data } = $props();

	const orient = $derived(data.orient);
	const description = $derived(
		orient?.guidelines?.[0] || `Browse ${data.total} entries in the ${data.kb} knowledge base.`
	);
</script>

<svelte:head>
	<title>{data.kb} — Pyrite Knowledge Base</title>
	<meta name="description" content={description} />
	<meta property="og:title" content="{data.kb} — Pyrite Knowledge Base" />
	<meta property="og:description" content={description} />
	<meta property="og:type" content="website" />
</svelte:head>

<nav class="mb-4 text-sm text-zinc-500">
	<a href="/site" class="hover:text-zinc-900 dark:hover:text-zinc-100">Home</a>
	<span class="mx-1">/</span>
	<span class="text-zinc-900 dark:text-zinc-100">{data.kb}</span>
</nav>

<h1 class="mb-2 text-3xl font-bold text-zinc-900 dark:text-zinc-100">{data.kb}</h1>
<p class="mb-6 text-zinc-500">{data.total} entries</p>

{#if orient}
	{#if orient.guidelines?.length > 0}
		<section class="mb-8">
			{#each orient.guidelines as guideline}
				<p class="mb-2 text-zinc-600 dark:text-zinc-400">{guideline}</p>
			{/each}
		</section>
	{/if}

	{#if orient.entry_types?.length > 0}
		<section class="mb-8">
			<h2 class="mb-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">Entry Types</h2>
			<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
				{#each orient.entry_types as et}
					<div class="rounded-lg border border-zinc-200 p-3 dark:border-zinc-700" style="border-left: 3px solid {typeColor(et.type)}">
						<div class="text-xl font-bold text-zinc-900 dark:text-zinc-100">{et.count}</div>
						<div class="text-sm text-zinc-500">{et.type}</div>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	{#if orient.top_tags?.length > 0}
		<section class="mb-8">
			<h2 class="mb-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">Top Tags</h2>
			<div class="flex flex-wrap gap-2">
				{#each orient.top_tags as tag}
					<span class="rounded-full bg-zinc-100 px-3 py-1 text-sm text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
						{tag.name} <span class="text-zinc-400">({tag.count})</span>
					</span>
				{/each}
			</div>
		</section>
	{/if}

	{#if orient.recent?.length > 0}
		<section class="mb-8">
			<h2 class="mb-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">Recent</h2>
			<div class="space-y-2">
				{#each orient.recent as entry}
					<a href="/site/{data.kb}/{encodeURIComponent(entry.id)}" class="block rounded-lg border border-zinc-200 bg-white px-4 py-3 transition-colors hover:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-800 dark:hover:border-zinc-500" style="border-left: 3px solid {typeColor(entry.entry_type)}">
						<div class="flex items-center gap-2">
							<span class="font-medium text-zinc-900 dark:text-zinc-100">{entry.title}</span>
							<span class="rounded px-1.5 py-0.5 text-xs font-medium" style="background-color: {typeColor(entry.entry_type)}20; color: {typeColor(entry.entry_type)}">{entry.entry_type}</span>
						</div>
					</a>
				{/each}
			</div>
		</section>
	{/if}
{/if}

{#if data.entries.length > 0}
	<section>
		<h2 class="mb-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">All Entries</h2>
		<div class="space-y-2">
			{#each data.entries as entry}
				<a href="/site/{data.kb}/{encodeURIComponent(entry.id)}" class="block rounded-lg border border-zinc-200 bg-white px-4 py-3 transition-colors hover:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-800 dark:hover:border-zinc-500" style="border-left: 3px solid {typeColor(entry.entry_type)}">
					<div class="flex items-center gap-2">
						<span class="font-medium text-zinc-900 dark:text-zinc-100">{entry.title}</span>
						<span class="rounded px-1.5 py-0.5 text-xs font-medium" style="background-color: {typeColor(entry.entry_type)}20; color: {typeColor(entry.entry_type)}">{entry.entry_type}</span>
					</div>
					{#if entry.summary}
						<p class="mt-1 text-sm text-zinc-500">{entry.summary}</p>
					{/if}
				</a>
			{/each}
		</div>
	</section>
{/if}
