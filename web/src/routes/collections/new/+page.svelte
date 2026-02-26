<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import QueryBuilder from '$lib/components/collection/QueryBuilder.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';

	let title = $state('');
	let description = $state('');
	let query = $state('');
	let collectionType = $state('generic');
	let collectionTypes: Record<string, { description: string; default_view: string; fields?: Record<string, unknown>; ai_instructions?: string; icon?: string }> = $state({
		generic: { description: 'General-purpose collection', default_view: 'list', icon: 'folder' }
	});

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
</script>

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
				disabled={!canSave}
				class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
			>
				Create Collection
			</button>
			<span class="text-xs text-zinc-400">
				Save is not yet wired up — backend create-collection endpoint coming soon.
			</span>
		</div>
	</div>
</div>
