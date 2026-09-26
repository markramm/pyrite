<script lang="ts">
	import { api, ApiError } from '$lib/api/client';
	import { goto } from '$app/navigation';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import TypeChoice from '$lib/components/entry/TypeChoice.svelte';
	import type { TypeSchemaInfo } from '$lib/api/types';

	let url = $state('');
	let title = $state('');
	let tags = $state('');
	let loading = $state(false);
	let error = $state('');
	let selectedKb = $state('');
	let typeSchemas = $state<Record<string, TypeSchemaInfo>>({});
	let declaredTypes = $state<string[]>([]);
	// '' means "not chosen yet". Never default to an arbitrary declared type
	// (round-1 cold read); the clip is blocked until a real choice exists.
	let entryType = $state('');
	let allowUndeclared = $state(false);
	let schemasLoading = $state(false);
	let schemasError = $state(false);

	// Guards against a stale response landing after a newer KB selection --
	// the same pattern search.svelte.ts uses (#367/#443): only the response
	// whose request id still matches the latest one gets applied.
	let schemasRequestId = 0;

	// Use the current KB from the store
	$effect(() => {
		if (kbStore.activeKB && !selectedKb) {
			selectedKb = kbStore.activeKB;
		}
	});

	$effect(() => {
		if (selectedKb) loadTypeSchemas(selectedKb);
	});

	async function loadTypeSchemas(kb: string) {
		const requestId = ++schemasRequestId;
		schemasLoading = true;
		schemasError = false;
		try {
			const res = await api.getTypeSchemas(kb);
			if (requestId !== schemasRequestId) return; // a newer KB selection has since started
			typeSchemas = res.types;
			declaredTypes = res.declared ?? [];
			// Reset the choice for the newly loaded KB rather than carry over
			// a type (or allow_undeclared) picked for a previous one.
			entryType = '';
			allowUndeclared = false;
		} catch {
			if (requestId !== schemasRequestId) return;
			typeSchemas = {};
			declaredTypes = [];
			schemasError = true;
		} finally {
			if (requestId === schemasRequestId) schemasLoading = false;
		}
	}

	function onTypeChoice(choice: { entryType: string; allowUndeclared: boolean }) {
		entryType = choice.entryType;
		allowUndeclared = choice.allowUndeclared;
	}

	const typeChoicePending = $derived(Object.keys(typeSchemas).length > 0 && !entryType);

	async function handleClip() {
		if (!url.trim()) {
			error = 'Please enter a URL';
			return;
		}
		if (!selectedKb) {
			error = 'Please select a knowledge base';
			return;
		}
		if (schemasLoading) {
			error = 'Still loading this KB\'s entry types -- please wait';
			return;
		}
		if (typeChoicePending) {
			error = 'Choose an entry type';
			return;
		}

		loading = true;
		error = '';

		try {
			const result = await api.clipUrl({
				url: url.trim(),
				kb: selectedKb,
				title: title.trim() || undefined,
				tags: tags.trim() ? tags.split(',').map((t) => t.trim()) : undefined,
				entry_type: entryType,
				...(allowUndeclared ? { allow_undeclared: true } : {})
			});

			// Redirect to the new entry
			goto(`/entries/${encodeURIComponent(result.id)}?kb=${encodeURIComponent(result.kb_name)}`);
		} catch (e) {
			error = e instanceof ApiError ? e.detail : e instanceof Error ? e.message : 'Failed to clip URL';
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Web Clipper — Pyrite</title>
</svelte:head>

<div class="mx-auto max-w-2xl p-6">
	<h1 class="mb-6 text-2xl font-bold text-zinc-900 dark:text-zinc-100">Web Clipper</h1>
	<p class="mb-6 text-zinc-600 dark:text-zinc-400">
		Clip a web page and save it as a knowledge base entry.
	</p>

	<form onsubmit={(e) => { e.preventDefault(); handleClip(); }} class="space-y-4">
		<div>
			<label for="url" class="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300"
				>URL</label
			>
			<input
				id="url"
				type="url"
				bind:value={url}
				placeholder="https://example.com/article"
				required
				class="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-zinc-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
			/>
		</div>

		<div>
			<label for="kb" class="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300"
				>Knowledge Base</label
			>
			<select
				id="kb"
				bind:value={selectedKb}
				class="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-zinc-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
			>
				{#each kbStore.kbs as kb}
					<option value={kb.name}>{kb.name}</option>
				{/each}
			</select>
		</div>

		<div>
			<label for="title" class="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300"
				>Title (optional, auto-detected)</label
			>
			<input
				id="title"
				type="text"
				bind:value={title}
				placeholder="Override page title"
				class="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-zinc-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
			/>
		</div>

		<div>
			<label for="tags" class="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300"
				>Tags (comma-separated)</label
			>
			<input
				id="tags"
				type="text"
				bind:value={tags}
				placeholder="research, web-clip"
				class="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-zinc-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
			/>
		</div>

		{#if schemasLoading}
			<p class="text-sm text-zinc-400" data-testid="type-schemas-loading">
				Loading entry types…
			</p>
		{:else if schemasError}
			<div class="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
				<p data-testid="type-schemas-error">Could not load this KB's entry types.</p>
				<button
					type="button"
					onclick={() => loadTypeSchemas(selectedKb)}
					class="mt-1 text-xs font-medium underline"
					data-testid="type-schemas-retry"
				>
					Retry
				</button>
			</div>
		{:else if Object.keys(typeSchemas).length > 0}
			<TypeChoice
				id="clip-entry-type"
				types={Object.keys(typeSchemas).sort()}
				declared={declaredTypes}
				value={entryType}
				onchange={onTypeChoice}
			/>
		{/if}

		{#if error}
			<div class="rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
				{error}
			</div>
		{/if}

		<button
			type="submit"
			disabled={loading || schemasLoading || schemasError || typeChoicePending}
			class="w-full rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
		>
			{#if loading}
				Clipping...
			{:else}
				Clip Page
			{/if}
		</button>
	</form>
</div>
