<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import ErrorState from '$lib/components/common/ErrorState.svelte';
	import { searchStore } from '$lib/stores/search.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { api } from '$lib/api/client';
	import { typeColor } from '$lib/constants';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	let searchInput = $state<HTMLInputElement | null>(null);
	let selectedKb = $state('');
	let selectedType = $state('');
	let entryTypes = $state<string[]>([]);

	function highlightSnippet(snippet: string, query: string): string {
		if (!query.trim()) return snippet;
		// Escape regex special characters
		const escaped = query.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
		const words = escaped.split(/\s+/).filter(Boolean);
		if (words.length === 0) return snippet;
		const pattern = new RegExp(`(${words.join('|')})`, 'gi');
		return snippet.replace(pattern, '<mark class="bg-gold-500/30 text-gold-300 rounded px-0.5">$1</mark>');
	}

	function formatRelativeDate(dateStr: string): string {
		const date = new Date(dateStr);
		if (isNaN(date.getTime())) return dateStr;
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
		if (diffDays === 0) return 'today';
		if (diffDays === 1) return 'yesterday';
		if (diffDays < 7) return `${diffDays} days ago`;
		if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
		if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
		return `${Math.floor(diffDays / 365)} years ago`;
	}

	function runSearch() {
		searchStore.execute({
			kb: selectedKb || undefined,
			type: selectedType || undefined,
			mode: searchStore.mode,
		});
	}

	function onSearchInput(e: Event) {
		const value = (e.target as HTMLInputElement).value;
		searchStore.setQuery(value);
	}

	function setMode(m: 'keyword' | 'semantic' | 'hybrid') {
		searchStore.mode = m;
		if (searchStore.query.trim()) {
			runSearch();
		}
	}

	function onKbChange() {
		if (searchStore.query.trim()) runSearch();
	}

	function onTypeChange() {
		if (searchStore.query.trim()) runSearch();
	}

	onMount(async () => {
		// Read initial query and mode from URL params
		const initialQ = $page.url.searchParams.get('q') ?? '';
		const initialMode = $page.url.searchParams.get('mode') as 'keyword' | 'semantic' | 'hybrid' | null;

		if (initialMode && ['keyword', 'semantic', 'hybrid'].includes(initialMode)) {
			searchStore.mode = initialMode;
		}

		// Focus the input
		searchInput?.focus();

		// Load entry types
		try {
			const res = await api.getEntryTypes();
			entryTypes = res.types;
		} catch {
			// Fall back gracefully
		}

		// Trigger search if there's an initial query
		if (initialQ) {
			searchStore.query = initialQ;
			runSearch();
		}
	});
</script>

<Topbar breadcrumbs={[{ label: 'Search' }]} />

<div class="flex flex-1 flex-col overflow-hidden">
	<!-- Search header area -->
	<div class="border-b border-zinc-200 bg-zinc-50 px-6 py-4 dark:border-zinc-800 dark:bg-zinc-900">
		<!-- Large search input -->
		<div class="relative mb-3">
			<div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
				<svg class="h-5 w-5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
			</div>
			<input
				bind:this={searchInput}
				type="text"
				value={searchStore.query}
				oninput={onSearchInput}
				placeholder="Search entries..."
				class="w-full rounded-lg border border-zinc-300 bg-white py-3 pl-12 pr-4 text-lg text-zinc-900 outline-none transition-colors placeholder:text-zinc-400 focus:border-gold-400 focus:ring-2 focus:ring-gold-400/20 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-gold-500"
			/>
		</div>

		<!-- Filter bar -->
		<div class="flex flex-wrap items-center gap-3">
			<!-- Mode buttons -->
			<div class="flex items-center rounded-lg border border-zinc-300 bg-white dark:border-zinc-700 dark:bg-zinc-800">
				{#each (['keyword', 'semantic', 'hybrid'] as const) as m}
					<button
						onclick={() => setMode(m)}
						class="rounded-lg px-3 py-1.5 text-sm font-medium transition-colors capitalize {searchStore.mode === m
							? 'bg-gold-500/20 text-gold-400 border border-gold-500/50'
							: 'text-zinc-500 hover:text-zinc-300'}"
					>
						{m}
					</button>
				{/each}
			</div>

			<!-- KB filter -->
			<select
				bind:value={selectedKb}
				onchange={onKbChange}
				class="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-sm text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
			>
				<option value="">All KBs</option>
				{#each kbStore.kbs as kb}
					<option value={kb.name}>{kb.name}</option>
				{/each}
			</select>

			<!-- Type filter -->
			<select
				bind:value={selectedType}
				onchange={onTypeChange}
				class="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-sm text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
			>
				<option value="">All types</option>
				{#each entryTypes as t}
					<option value={t}>{t}</option>
				{/each}
			</select>

			<!-- Result count -->
			{#if !searchStore.loading && searchStore.query.trim() && searchStore.results.length > 0}
				<span class="ml-auto text-sm text-zinc-500">
					{searchStore.results.length} result{searchStore.results.length === 1 ? '' : 's'}
				</span>
			{/if}
		</div>
	</div>

	<!-- Results area -->
	<div class="flex-1 overflow-y-auto p-6">
		{#if searchStore.loading}
			<div class="flex items-center justify-center py-16 text-zinc-400">
				<svg class="mr-3 h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<span class="text-sm">Searching...</span>
			</div>
		{:else if searchStore.error}
			<ErrorState message={searchStore.error} onretry={runSearch} />
		{:else if searchStore.query.trim() && searchStore.results.length === 0}
			<div class="flex flex-col items-center justify-center py-16 text-center">
				<svg class="mb-4 h-12 w-12 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<p class="mb-1 text-lg font-medium text-zinc-300">No results found</p>
				<p class="text-sm text-zinc-500">No results for "{searchStore.query}"</p>
				{#if searchStore.mode === 'keyword'}
					<p class="mt-2 text-xs text-zinc-600">Try switching to <button class="text-gold-400 hover:underline" onclick={() => setMode('hybrid')}>hybrid</button> or <button class="text-gold-400 hover:underline" onclick={() => setMode('semantic')}>semantic</button> mode</p>
				{/if}
			</div>
		{:else if !searchStore.query.trim()}
			<div class="flex flex-col items-center justify-center py-16 text-center">
				<svg class="mb-4 h-12 w-12 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<p class="mb-1 text-lg font-medium text-zinc-400">Search your knowledge base</p>
				<p class="text-sm text-zinc-500">Type to search across all entries, notes, and documents</p>
			</div>
		{:else}
			<div class="space-y-2">
				{#each searchStore.results as result (result.id)}
					<a
						href="/entries/{encodeURIComponent(result.id)}"
						class="block rounded-lg border border-zinc-200 bg-white p-4 transition-colors hover:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-800/50 dark:hover:border-zinc-500"
						style="border-left: 3px solid {typeColor(result.entry_type)}"
					>
						<div class="mb-1.5 flex flex-wrap items-center gap-2">
							<!-- Title -->
							<span class="font-medium text-zinc-900 dark:text-zinc-100">{result.title}</span>

							<!-- Type badge -->
							<span
								class="rounded px-1.5 py-0.5 text-xs font-medium"
								style="background-color: {typeColor(result.entry_type)}20; color: {typeColor(result.entry_type)}"
							>
								{result.entry_type}
							</span>

							<!-- KB badge -->
							<span class="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400">
								{result.kb_name}
							</span>

							<!-- Date -->
							{#if result.date}
								<span class="ml-auto text-xs text-zinc-400">{formatRelativeDate(result.date)}</span>
							{/if}
						</div>

						<!-- Snippet with highlighting -->
						{#if result.snippet}
							<p class="mb-2 text-sm leading-relaxed text-zinc-500 dark:text-zinc-400">
								<!-- eslint-disable-next-line svelte/no-at-html-tags -->
								{@html highlightSnippet(result.snippet, searchStore.query)}
							</p>
						{/if}

						<!-- Tags -->
						{#if result.tags.length > 0}
							<div class="flex flex-wrap gap-1">
								{#each result.tags as tag}
									<span class="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500 dark:bg-zinc-700/60 dark:text-zinc-400">
										{tag}
									</span>
								{/each}
							</div>
						{/if}
					</a>
				{/each}
			</div>
		{/if}
	</div>
</div>
