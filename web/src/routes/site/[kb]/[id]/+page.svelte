<script lang="ts">
	import { typeColor } from '$lib/constants';
	import type { PageData } from './$types';
	let { data } = $props();

	const entry = $derived(data.entry);
	const description = $derived(
		entry?.summary || (entry?.body ? entry.body.slice(0, 160).replace(/[#*_\[\]]/g, '') + '...' : '')
	);

	const schemaType: Record<string, string> = {
		note: 'Article', person: 'Person', organization: 'Organization',
		event: 'Event', source: 'ScholarlyArticle', concept: 'Article',
		writing: 'Article', era: 'Article', component: 'SoftwareSourceCode',
	};

	function bodyToHtml(body: string): string {
		return body
			.replace(/^### (.+)$/gm, '<h3 class="mt-6 mb-2 text-lg font-semibold text-zinc-900 dark:text-zinc-100">$1</h3>')
			.replace(/^## (.+)$/gm, '<h2 class="mt-8 mb-3 text-xl font-bold text-zinc-900 dark:text-zinc-100">$1</h2>')
			.replace(/^# (.+)$/gm, '<h1 class="mt-8 mb-3 text-2xl font-bold text-zinc-900 dark:text-zinc-100">$1</h1>')
			.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
			.replace(/\*(.+?)\*/g, '<em>$1</em>')
			.replace(/\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g, (_, target, label) => {
				const parts = target.split(':');
				if (parts.length === 2) {
					return `<a href="/site/${encodeURIComponent(parts[0])}/${encodeURIComponent(parts[1])}" class="text-gold-500 hover:underline">${label || parts[1]}</a>`;
				}
				return `<a href="/site/${data.kb}/${encodeURIComponent(target)}" class="text-gold-500 hover:underline">${label || target}</a>`;
			})
			.replace(/^- (.+)$/gm, '<li class="ml-4 text-zinc-700 dark:text-zinc-300">$1</li>')
			.replace(/\n\n/g, '</p><p class="mb-4 leading-relaxed text-zinc-700 dark:text-zinc-300">')
			.replace(/^/, '<p class="mb-4 leading-relaxed text-zinc-700 dark:text-zinc-300">')
			+ '</p>';
	}
</script>

<svelte:head>
	{#if entry}
		<title>{entry.title} — {data.kb} | Pyrite</title>
		<meta name="description" content={description} />
		<meta property="og:title" content="{entry.title} — {data.kb}" />
		<meta property="og:description" content={description} />
		<meta property="og:type" content="article" />
		{@html `<script type="application/ld+json">${JSON.stringify({
			"@context": "https://schema.org",
			"@type": schemaType[entry.entry_type] ?? "Article",
			"name": entry.title,
			"description": description,
			...(entry.date ? { "datePublished": entry.date } : {}),
			...(entry.tags?.length ? { "keywords": entry.tags.join(", ") } : {}),
		})}</script>`}
	{:else}
		<title>Not Found — Pyrite</title>
	{/if}
</svelte:head>

{#if !entry}
	<div class="py-16 text-center">
		<h1 class="mb-2 text-2xl font-bold text-zinc-400">Entry not found</h1>
		<p class="text-zinc-500">The entry "{data.id}" was not found in {data.kb}.</p>
		<a href="/site/{data.kb}" class="mt-4 inline-block text-gold-500 hover:underline">Back to {data.kb}</a>
	</div>
{:else}
	<nav class="mb-4 text-sm text-zinc-500">
		<a href="/site" class="hover:text-zinc-900 dark:hover:text-zinc-100">Home</a>
		<span class="mx-1">/</span>
		<a href="/site/{data.kb}" class="hover:text-zinc-900 dark:hover:text-zinc-100">{data.kb}</a>
		<span class="mx-1">/</span>
		<span class="text-zinc-900 dark:text-zinc-100">{entry.title}</span>
	</nav>

	<header class="mb-6">
		<div class="flex items-center gap-3">
			<h1 class="text-3xl font-bold text-zinc-900 dark:text-zinc-100">{entry.title}</h1>
			<span class="rounded px-2 py-0.5 text-xs font-medium" style="background-color: {typeColor(entry.entry_type)}20; color: {typeColor(entry.entry_type)}">{entry.entry_type}</span>
		</div>
		{#if entry.tags?.length > 0}
			<div class="mt-3 flex flex-wrap gap-1">
				{#each entry.tags as tag}
					<span class="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">{tag}</span>
				{/each}
			</div>
		{/if}
		<div class="mt-2 flex items-center gap-3 text-sm text-zinc-500">
			{#if entry.date}<span>{entry.date}</span>{/if}
			<a href="/entries/{encodeURIComponent(entry.id)}?kb={encodeURIComponent(data.kb)}" class="ml-auto text-xs text-zinc-400 hover:text-gold-500">Edit on Pyrite</a>
		</div>
	</header>

	{#if entry.body}
		<article class="prose prose-zinc max-w-none dark:prose-invert">
			{@html bodyToHtml(entry.body)}
		</article>
	{/if}

	{#if entry.backlinks?.length > 0}
		<section class="mt-8 border-t border-zinc-200 pt-6 dark:border-zinc-800">
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">Linked from</h2>
			<div class="space-y-1">
				{#each entry.backlinks as bl}
					<a href="/site/{bl.kb_name ?? data.kb}/{encodeURIComponent(bl.id)}" class="block text-sm text-gold-500 hover:underline">{bl.title ?? bl.id}</a>
				{/each}
			</div>
		</section>
	{/if}

	{#if entry.outlinks?.length > 0}
		<section class="mt-6 border-t border-zinc-200 pt-6 dark:border-zinc-800">
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">Links to</h2>
			<div class="space-y-1">
				{#each entry.outlinks as ol}
					<a href="/site/{ol.kb_name ?? data.kb}/{encodeURIComponent(ol.id)}" class="block text-sm text-gold-500 hover:underline">{ol.title ?? ol.id}</a>
				{/each}
			</div>
		</section>
	{/if}
{/if}
