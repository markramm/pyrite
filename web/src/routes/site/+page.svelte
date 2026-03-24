<script lang="ts">
	import type { PageData } from './$types';
	let { data } = $props();
</script>

<svelte:head>
	<title>Pyrite Knowledge Base</title>
	<meta name="description" content="Browse knowledge bases on systems thinking, lean, agile, and more." />
	<meta property="og:title" content="Pyrite Knowledge Base" />
	<meta property="og:description" content="Browse knowledge bases on systems thinking, lean, agile, and more." />
	<meta property="og:type" content="website" />
</svelte:head>

<h1 class="mb-2 text-3xl font-bold text-zinc-900 dark:text-zinc-100">Knowledge Bases</h1>
<p class="mb-8 text-zinc-500">Browse curated knowledge bases on systems thinking, lean, agile, and more.</p>

{#if data.kbs.length === 0}
	<p class="text-zinc-500">No knowledge bases available.</p>
{:else}
	<div class="grid gap-4 sm:grid-cols-2">
		{#each data.kbs as kb}
			<a
				href="/site/{kb.name}"
				class="rounded-lg border border-zinc-200 bg-white p-5 transition-colors hover:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-800 dark:hover:border-zinc-500"
			>
				<h2 class="mb-1 text-lg font-semibold text-zinc-900 dark:text-zinc-100">{kb.name}</h2>
				{#if kb.description}
					<p class="mb-2 text-sm text-zinc-500">{kb.description}</p>
				{/if}
				<span class="text-xs text-zinc-400">{kb.entries ?? 0} entries</span>
			</a>
		{/each}
	</div>
{/if}
