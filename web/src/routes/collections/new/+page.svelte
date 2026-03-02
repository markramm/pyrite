<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import QueryBuilder from '$lib/components/collection/QueryBuilder.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { api } from '$lib/api/client';
	import { goto } from '$app/navigation';
	import { uiStore } from '$lib/stores/ui.svelte';

	let title = $state('');
	let description = $state('');
	let query = $state('');
	let collectionType = $state('generic');
	let collectionTypes: Record<string, { description: string; default_view: string; fields?: Record<string, unknown>; ai_instructions?: string; icon?: string }> = $state({
		generic: { description: 'General-purpose collection', default_view: 'list', icon: 'folder' }
	});
	let saving = $state(false);
	let saveError = $state<string | null>(null);

	const kb = $derived(kbStore.activeKB ?? '');

	async function loadCollectionTypes() {
		try {
			const res = await fetch('/api/collections/types');
			if (res.ok) {
				const data = await res.json();
				collectionTypes = data.types;
			}
		} catch {
			// Keep defaults
		}
	}

	$effect(() => {
		loadCollectionTypes();
	});

	const breadcrumbs = [
		{ label: 'Collections', href: '/collections' },
		{ label: 'New Virtual Collection' }
	];

	const canSave = $derived(title.trim() !== '' && query.trim() !== '');

	async function handleSave() {
		if (!canSave) return;
		saving = true;
		saveError = null;
		try {
			const result = await api.createCollection({
				kb,
				title: title.trim(),
				query: query.trim(),
				description: description.trim() || undefined,
				collection_type: collectionType,
			});
			uiStore.toast('Collection created', 'success');
			goto(`/collections/${encodeURIComponent(result.id)}?kb=${encodeURIComponent(result.kb_name)}`);
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to create collection';
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head><title>New Collection — Pyrite</title></svelte:head>

<Topbar {breadcrumbs} />

<div class="flex-1 overflow-y-auto p-6">
	<h1 class="mb-6 text-2xl font-bold">New Virtual Collection</h1>

	<div class="max-w-3xl space-y-6">
		<div>
			<label class="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300" for="title"
				>Title</label
			>
			<input
				id="title"
				bind:value={title}
				type="text"
				placeholder="My Collection"
				class="w-full rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
			/>
		</div>

		<div>
			<label class="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300" for="desc"
				>Description</label
			>
			<input
				id="desc"
				bind:value={description}
				type="text"
				placeholder="Optional description"
				class="w-full rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
			/>
		</div>

		<div>
			<label class="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300" for="collection-type"
				>Collection Type</label
			>
			<select
				id="collection-type"
				bind:value={collectionType}
				class="w-full rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
			>
				{#each Object.entries(collectionTypes) as [key, ct]}
					<option value={key}>{key} — {ct.description}</option>
				{/each}
			</select>
		</div>

		<div>
			<label class="mb-2 block text-sm font-medium text-zinc-700 dark:text-zinc-300" for="query-builder">Query</label>
			<QueryBuilder {kb} onQueryChange={(q) => (query = q)} />
		</div>

		<div class="flex items-center gap-3 border-t border-zinc-200 pt-6 dark:border-zinc-700">
			<button
				type="button"
				disabled={!canSave || saving}
				onclick={handleSave}
				class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
			>
				{saving ? 'Creating…' : 'Create Collection'}
			</button>
			{#if saveError}
				<span class="text-sm text-red-500">{saveError}</span>
			{/if}
		</div>
	</div>
</div>
