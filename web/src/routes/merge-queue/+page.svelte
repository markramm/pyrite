<script lang="ts">
	import { api } from '$lib/api/client';
	import { authStore } from '$lib/stores/auth.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { onMount } from 'svelte';

	type Submission = {
		username: string;
		kb_name: string;
		branch: string;
		status: string;
		submitted_at: string | null;
		changes_count: number;
	};

	let submissions = $state<Submission[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let selectedKb = $state('');
	let feedback = $state<{ ok: boolean; message: string } | null>(null);

	// Expanded diff view
	let expandedUser = $state<string | null>(null);
	let diffData = $state<{ diff: string; stat: string } | null>(null);
	let diffLoading = $state(false);

	// Reject dialog
	let rejectingUser = $state<string | null>(null);
	let rejectFeedback = $state('');
	let rejectSubmitting = $state(false);

	const isAdmin = $derived(authStore.isAdmin);
	const kbs = $derived(kbStore.kbs);

	async function loadQueue() {
		loading = true;
		error = null;
		try {
			const result = await api.getMergeQueue(selectedKb || undefined);
			submissions = result.submissions;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load merge queue';
		} finally {
			loading = false;
		}
	}

	async function toggleDiff(username: string, kb: string) {
		if (expandedUser === username) {
			expandedUser = null;
			diffData = null;
			return;
		}
		expandedUser = username;
		diffLoading = true;
		try {
			diffData = await api.getMergeQueueDiff(username, kb);
		} catch {
			diffData = null;
		} finally {
			diffLoading = false;
		}
	}

	async function handleMerge(username: string, kb: string) {
		feedback = null;
		try {
			const result = await api.mergeWorktree(username, kb);
			if (result.merged) {
				feedback = { ok: true, message: `Merged ${username}'s changes into main` };
				submissions = submissions.filter(s => s.username !== username);
			} else {
				feedback = { ok: false, message: result.message };
			}
		} catch (err) {
			feedback = { ok: false, message: err instanceof Error ? err.message : 'Merge failed' };
		}
	}

	async function handleReject(username: string, kb: string) {
		rejectSubmitting = true;
		try {
			await api.rejectWorktree(username, kb, rejectFeedback);
			feedback = { ok: true, message: `Rejected ${username}'s submission` };
			submissions = submissions.filter(s => s.username !== username);
			rejectingUser = null;
			rejectFeedback = '';
		} catch (err) {
			feedback = { ok: false, message: err instanceof Error ? err.message : 'Reject failed' };
		} finally {
			rejectSubmitting = false;
		}
	}

	onMount(() => {
		if (kbs.length > 0 && !selectedKb) {
			selectedKb = kbs[0].name;
		}
		loadQueue();
	});

	$effect(() => {
		if (selectedKb) loadQueue();
	});
</script>

<svelte:head>
	<title>Merge Queue - Pyrite</title>
</svelte:head>

<div class="mx-auto max-w-5xl space-y-6 p-6">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-zinc-100">Merge Queue</h1>
			<p class="text-sm text-zinc-400">Review and integrate contributor submissions</p>
		</div>
		<div class="flex items-center gap-3">
			{#if kbs.length > 1}
				<select
					bind:value={selectedKb}
					class="rounded-md border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-200"
				>
					<option value="">All KBs</option>
					{#each kbs as kb}
						<option value={kb.name}>{kb.name}</option>
					{/each}
				</select>
			{/if}
			<button
				onclick={loadQueue}
				class="rounded-md border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800"
			>
				Refresh
			</button>
		</div>
	</div>

	{#if !isAdmin}
		<div class="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-400">
			Admin access required to manage the merge queue.
		</div>
	{:else}
		<!-- Feedback banner -->
		{#if feedback}
			<div
				class="rounded-lg border p-3 text-sm {feedback.ok
					? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
					: 'border-red-500/30 bg-red-500/10 text-red-400'}"
			>
				{feedback.message}
			</div>
		{/if}

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<svg
					class="h-6 w-6 animate-spin text-zinc-400"
					fill="none"
					viewBox="0 0 24 24"
				>
					<circle
						class="opacity-25"
						cx="12"
						cy="12"
						r="10"
						stroke="currentColor"
						stroke-width="4"
					></circle>
					<path
						class="opacity-75"
						fill="currentColor"
						d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
					></path>
				</svg>
				<span class="ml-2 text-zinc-400">Loading submissions...</span>
			</div>
		{:else if error}
			<div class="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-400">
				{error}
			</div>
		{:else if submissions.length === 0}
			<div class="flex flex-col items-center justify-center py-16 text-center">
				<svg class="mb-4 h-12 w-12 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
						d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<h3 class="text-lg font-medium text-zinc-400">No pending submissions</h3>
				<p class="mt-1 text-sm text-zinc-500">All contributor changes have been reviewed.</p>
			</div>
		{:else}
			<div class="space-y-3">
				{#each submissions as sub}
					<div class="rounded-lg border border-zinc-700 bg-zinc-800/50">
						<!-- Header row -->
						<div class="flex items-center justify-between p-4">
							<div class="flex items-center gap-3">
								<div
									class="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-700 text-sm font-medium text-zinc-300"
								>
									{sub.username.charAt(0).toUpperCase()}
								</div>
								<div>
									<span class="font-medium text-zinc-200">{sub.username}</span>
									<span class="ml-2 text-sm text-zinc-500">{sub.kb_name}</span>
								</div>
								<span
									class="rounded-full px-2 py-0.5 text-xs font-medium {sub.changes_count > 5
										? 'bg-amber-500/20 text-amber-400'
										: 'bg-zinc-700 text-zinc-400'}"
								>
									{sub.changes_count} {sub.changes_count === 1 ? 'change' : 'changes'}
								</span>
							</div>
							<div class="flex items-center gap-2">
								{#if sub.submitted_at}
									<span class="text-xs text-zinc-500">
										{new Date(sub.submitted_at).toLocaleDateString()}
									</span>
								{/if}
								<button
									onclick={() => toggleDiff(sub.username, sub.kb_name)}
									class="rounded-md border border-zinc-600 px-3 py-1 text-sm text-zinc-300 hover:bg-zinc-700"
								>
									{expandedUser === sub.username ? 'Hide' : 'Diff'}
								</button>
								<button
									onclick={() => handleMerge(sub.username, sub.kb_name)}
									class="rounded-md bg-emerald-600 px-3 py-1 text-sm font-medium text-white hover:bg-emerald-500"
								>
									Merge
								</button>
								<button
									onclick={() => {
										rejectingUser = sub.username;
										rejectFeedback = '';
									}}
									class="rounded-md border border-red-500/50 px-3 py-1 text-sm text-red-400 hover:bg-red-500/10"
								>
									Reject
								</button>
							</div>
						</div>

						<!-- Reject feedback dialog -->
						{#if rejectingUser === sub.username}
							<div class="border-t border-zinc-700 p-4">
								<textarea
									bind:value={rejectFeedback}
									placeholder="Feedback for the contributor (optional)..."
									class="w-full rounded-md border border-zinc-600 bg-zinc-900 p-2 text-sm text-zinc-200 placeholder-zinc-500"
									rows="2"
								></textarea>
								<div class="mt-2 flex gap-2">
									<button
										onclick={() => handleReject(sub.username, sub.kb_name)}
										disabled={rejectSubmitting}
										class="rounded-md bg-red-600 px-3 py-1 text-sm text-white hover:bg-red-500 disabled:opacity-50"
									>
										{rejectSubmitting ? 'Rejecting...' : 'Confirm Reject'}
									</button>
									<button
										onclick={() => {
											rejectingUser = null;
										}}
										class="rounded-md border border-zinc-600 px-3 py-1 text-sm text-zinc-400 hover:bg-zinc-700"
									>
										Cancel
									</button>
								</div>
							</div>
						{/if}

						<!-- Diff view -->
						{#if expandedUser === sub.username}
							<div class="border-t border-zinc-700 p-4">
								{#if diffLoading}
									<div class="flex items-center gap-2 text-sm text-zinc-400">
										<svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
											<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
											<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
										</svg>
										Loading diff...
									</div>
								{:else if diffData}
									{#if diffData.stat}
										<div class="mb-3 text-sm text-zinc-400">
											<pre class="whitespace-pre-wrap font-mono text-xs">{diffData.stat}</pre>
										</div>
									{/if}
									{#if diffData.diff}
										<pre
											class="max-h-96 overflow-auto rounded-md bg-zinc-900 p-3 font-mono text-xs text-zinc-300"
										>{diffData.diff}</pre>
									{:else}
										<p class="text-sm text-zinc-500">No diff available</p>
									{/if}
								{:else}
									<p class="text-sm text-zinc-500">Failed to load diff</p>
								{/if}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>
