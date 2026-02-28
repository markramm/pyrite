<script lang="ts">
	import { api } from '$lib/api/client';
	import { goto } from '$app/navigation';
	import { kbStore } from '$lib/stores/kbs.svelte';

	let url = $state('');
	let title = $state('');
	let tags = $state('');
	let loading = $state(false);
	let error = $state('');
	let selectedKb = $state('');

	// Use the current KB from the store
	$effect(() => {
		if (kbStore.activeKB && !selectedKb) {
			selectedKb = kbStore.activeKB;
		}
	});

	async function handleClip() {
		if (!url.trim()) {
			error = 'Please enter a URL';
			return;
		}
		if (!selectedKb) {
			error = 'Please select a knowledge base';
			return;
		}

		loading = true;
		error = '';

		try {
			const result = await api.clipUrl({
				url: url.trim(),
				kb: selectedKb,
				title: title.trim() || undefined,
				tags: tags.trim() ? tags.split(',').map((t) => t.trim()) : undefined
			});

			// Redirect to the new entry
			goto(`/entries/${encodeURIComponent(result.id)}?kb=${encodeURIComponent(result.kb_name)}`);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to clip URL';
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Web Clipper — Pyrite</title>
</svelte:head>

<div class="mx-auto max-w-2xl p-6">
	<h1 class="mb-6 text-2xl font-bold text-gray-900 dark:text-gray-100">Web Clipper</h1>
	<p class="mb-6 text-gray-600 dark:text-gray-400">
		Clip a web page and save it as a knowledge base entry.
	</p>

	<form onsubmit={(e) => { e.preventDefault(); handleClip(); }} class="space-y-4">
		<div>
			<label for="url" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
				>URL</label
			>
			<input
				id="url"
				type="url"
				bind:value={url}
				placeholder="https://example.com/article"
				required
				class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
			/>
		</div>

		<div>
			<label for="kb" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
				>Knowledge Base</label
			>
			<select
				id="kb"
				bind:value={selectedKb}
				class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
			>
				{#each kbStore.kbs as kb}
					<option value={kb.name}>{kb.name}</option>
				{/each}
			</select>
		</div>

		<div>
			<label for="title" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
				>Title (optional, auto-detected)</label
			>
			<input
				id="title"
				type="text"
				bind:value={title}
				placeholder="Override page title"
				class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
			/>
		</div>

		<div>
			<label for="tags" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
				>Tags (comma-separated)</label
			>
			<input
				id="tags"
				type="text"
				bind:value={tags}
				placeholder="research, web-clip"
				class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
			/>
		</div>

		{#if error}
			<div class="rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
				{error}
			</div>
		{/if}

		<button
			type="submit"
			disabled={loading}
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
