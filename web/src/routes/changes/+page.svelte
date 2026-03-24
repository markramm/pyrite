<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import ErrorState from '$lib/components/common/ErrorState.svelte';
	import { api } from '$lib/api/client';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { typeColor } from '$lib/constants';
	import type { PendingChange, PendingChangesResponse } from '$lib/api/types';
	import { onMount } from 'svelte';

	let selectedKb = $state('');
	let data = $state<PendingChangesResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let expandedFile = $state<string | null>(null);

	// Publish state
	let publishing = $state(false);
	let publishSummary = $state('');
	let showPublishDialog = $state(false);
	let publishResult = $state<{ ok: boolean; message: string } | null>(null);

	async function loadChanges() {
		if (!selectedKb) {
			data = null;
			loading = false;
			return;
		}
		loading = true;
		error = null;
		publishResult = null;
		try {
			data = await api.getPendingChanges(selectedKb);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load changes';
		} finally {
			loading = false;
		}
	}

	async function handlePublish() {
		if (!selectedKb) return;
		publishing = true;
		publishResult = null;
		try {
			const result = await api.publishChanges(selectedKb, publishSummary || undefined);
			if (result.success) {
				const msg = result.entries_published > 0
					? `Published ${result.entries_published} change${result.entries_published === 1 ? '' : 's'}${result.push_error ? ' (push failed: ' + result.push_error + ')' : ''}`
					: 'Nothing to publish';
				publishResult = { ok: true, message: msg };
				showPublishDialog = false;
				publishSummary = '';
				await loadChanges();
			} else {
				publishResult = { ok: false, message: result.error ?? 'Publish failed' };
			}
		} catch (err) {
			publishResult = { ok: false, message: err instanceof Error ? err.message : 'Publish failed' };
		} finally {
			publishing = false;
		}
	}

	function toggleExpand(filePath: string) {
		expandedFile = expandedFile === filePath ? null : filePath;
	}

	function stripFrontmatter(content: string | null): string {
		if (!content) return '';
		if (!content.startsWith('---')) return content;
		const parts = content.split('---', 3);
		return parts.length >= 3 ? parts[2].trim() : content;
	}

	onMount(() => {
		kbStore.load();
	});

	// Auto-select first KB and load
	$effect(() => {
		if (!selectedKb && kbStore.kbs.length > 0) {
			selectedKb = kbStore.activeKB || kbStore.kbs[0].name;
		}
	});

	$effect(() => {
		if (selectedKb) loadChanges();
	});

	const changeTypeLabel: Record<string, string> = {
		created: 'New',
		modified: 'Modified',
		deleted: 'Removed',
	};

	const changeTypeColor: Record<string, string> = {
		created: 'bg-emerald-500/20 text-emerald-400',
		modified: 'bg-blue-500/20 text-blue-400',
		deleted: 'bg-red-500/20 text-red-400',
	};

	const canPublish = $derived(authStore.isAdmin);
</script>

<svelte:head><title>Pending Changes — Pyrite</title></svelte:head>

<Topbar breadcrumbs={[{ label: 'Changes' }]} />

<div class="flex flex-1 flex-col overflow-hidden">
	<!-- Header -->
	<div class="border-b border-zinc-200 bg-zinc-50 px-6 py-4 dark:border-zinc-800 dark:bg-zinc-900">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-3">
				<h1 class="text-lg font-semibold text-zinc-900 dark:text-zinc-100">Pending Changes</h1>
				<select
					bind:value={selectedKb}
					class="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800"
				>
					{#each kbStore.kbs as kb}
						<option value={kb.name}>{kb.name}</option>
					{/each}
				</select>
				{#if data && data.summary.total > 0}
					<span class="rounded-full bg-gold-500/20 px-2 py-0.5 text-xs font-medium text-gold-400">
						{data.summary.total} change{data.summary.total === 1 ? '' : 's'}
					</span>
				{/if}
			</div>

			{#if canPublish && data && data.summary.total > 0}
				<button
					onclick={() => { showPublishDialog = true; publishSummary = ''; }}
					class="flex items-center gap-2 rounded-lg bg-gold-500 px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-gold-400"
				>
					<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
					</svg>
					Publish
				</button>
			{/if}
		</div>

		<!-- Publish dialog -->
		{#if showPublishDialog}
			<div class="mt-3 rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800">
				<p class="mb-2 text-sm text-zinc-500">Add an optional note about these changes:</p>
				<input
					type="text"
					bind:value={publishSummary}
					placeholder="e.g., Updated research findings..."
					onkeydown={(e) => { if (e.key === 'Enter') handlePublish(); }}
					class="mb-3 w-full rounded border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-gold-400 dark:border-zinc-700 dark:bg-zinc-900"
				/>
				<div class="flex items-center gap-2">
					<button
						onclick={handlePublish}
						disabled={publishing}
						class="rounded-lg bg-gold-500 px-4 py-1.5 text-sm font-medium text-zinc-900 hover:bg-gold-400 disabled:opacity-50"
					>
						{publishing ? 'Publishing...' : `Publish ${data?.summary.total ?? 0} change${(data?.summary.total ?? 0) === 1 ? '' : 's'}`}
					</button>
					<button
						onclick={() => (showPublishDialog = false)}
						class="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm text-zinc-500 hover:text-zinc-300 dark:border-zinc-700"
					>
						Cancel
					</button>
				</div>
			</div>
		{/if}
	</div>

	<!-- Feedback -->
	{#if publishResult}
		<div class="mx-6 mt-4 rounded-lg px-4 py-3 text-sm {publishResult.ok ? 'border border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border border-red-500/30 bg-red-500/10 text-red-400'}">
			{publishResult.message}
		</div>
	{/if}

	<!-- Content -->
	<div class="flex-1 overflow-y-auto p-6">
		{#if loading}
			<div class="flex items-center justify-center py-16 text-zinc-400">
				<svg class="mr-3 h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				Loading changes...
			</div>
		{:else if error}
			<ErrorState message={error} onretry={loadChanges} />
		{:else if !data || data.changes.length === 0}
			<div class="flex flex-col items-center justify-center py-16 text-center">
				<svg class="mb-4 h-12 w-12 text-emerald-500/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<p class="mb-1 text-lg font-medium text-zinc-400">All published</p>
				<p class="text-sm text-zinc-500">No pending changes in {selectedKb}</p>
			</div>
		{:else}
			<div class="mx-auto max-w-3xl space-y-2">
				<!-- Summary bar -->
				<div class="mb-4 flex items-center gap-3 text-sm text-zinc-500">
					{#if data.summary.created > 0}
						<span class="flex items-center gap-1">
							<span class="h-2 w-2 rounded-full bg-emerald-500"></span>
							{data.summary.created} new
						</span>
					{/if}
					{#if data.summary.modified > 0}
						<span class="flex items-center gap-1">
							<span class="h-2 w-2 rounded-full bg-blue-500"></span>
							{data.summary.modified} modified
						</span>
					{/if}
					{#if data.summary.deleted > 0}
						<span class="flex items-center gap-1">
							<span class="h-2 w-2 rounded-full bg-red-500"></span>
							{data.summary.deleted} removed
						</span>
					{/if}
				</div>

				<!-- Change list -->
				{#each data.changes as change (change.file_path)}
					<div class="rounded-lg border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-800">
						<!-- Change header -->
						<button
							onclick={() => toggleExpand(change.file_path)}
							class="flex w-full items-center justify-between px-4 py-3 text-left"
						>
							<div class="flex items-center gap-2">
								<span class="rounded px-1.5 py-0.5 text-xs font-medium {changeTypeColor[change.change_type]}">
									{changeTypeLabel[change.change_type]}
								</span>
								<span class="font-medium text-zinc-900 dark:text-zinc-100">{change.title}</span>
								<span
									class="rounded px-1.5 py-0.5 text-xs"
									style="background-color: {typeColor(change.entry_type)}20; color: {typeColor(change.entry_type)}"
								>
									{change.entry_type}
								</span>
							</div>
							<svg
								class="h-4 w-4 text-zinc-400 transition-transform {expandedFile === change.file_path ? 'rotate-180' : ''}"
								fill="none" viewBox="0 0 24 24" stroke="currentColor"
							>
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
							</svg>
						</button>

						<!-- Expanded diff view -->
						{#if expandedFile === change.file_path}
							<div class="border-t border-zinc-100 px-4 py-3 dark:border-zinc-700">
								{#if change.change_type === 'created'}
									<div class="rounded bg-emerald-500/5 p-3">
										<p class="mb-1 text-xs font-medium text-emerald-500">New entry</p>
										<pre class="whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">{stripFrontmatter(change.current_body)}</pre>
									</div>
								{:else if change.change_type === 'deleted'}
									<div class="rounded bg-red-500/5 p-3">
										<p class="mb-1 text-xs font-medium text-red-400">Removed</p>
										<pre class="whitespace-pre-wrap text-sm text-zinc-500 line-through">{stripFrontmatter(change.previous_body)}</pre>
									</div>
								{:else}
									<!-- Modified: show before/after -->
									<div class="grid grid-cols-2 gap-3">
										<div class="rounded bg-red-500/5 p-3">
											<p class="mb-1 text-xs font-medium text-red-400">Before</p>
											<pre class="whitespace-pre-wrap text-sm text-zinc-500">{stripFrontmatter(change.previous_body)}</pre>
										</div>
										<div class="rounded bg-emerald-500/5 p-3">
											<p class="mb-1 text-xs font-medium text-emerald-500">After</p>
											<pre class="whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">{stripFrontmatter(change.current_body)}</pre>
										</div>
									</div>
								{/if}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
