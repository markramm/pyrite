<!--
  VersionHistoryPanel: Shows git version history for an entry.
  Displayed as a side panel similar to BacklinksPanel.
-->
<script lang="ts">
	import type { EntryVersion } from '$lib/api/types';
	import { api } from '$lib/api/client';

	interface Props {
		entryId: string;
		kbName: string;
	}

	let { entryId, kbName }: Props = $props();

	let versions = $state<EntryVersion[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	$effect(() => {
		loadVersions();
	});

	async function loadVersions() {
		loading = true;
		error = null;
		try {
			const resp = await api.getEntryVersions(entryId, kbName);
			versions = resp.versions;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load versions';
		} finally {
			loading = false;
		}
	}

	function formatDate(dateStr: string): string {
		try {
			const d = new Date(dateStr);
			return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
		} catch {
			return dateStr;
		}
	}

	function formatTime(dateStr: string): string {
		try {
			const d = new Date(dateStr);
			return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
		} catch {
			return '';
		}
	}
</script>

<div class="flex h-full flex-col overflow-hidden">
	<div
		class="flex items-center justify-between border-b border-zinc-200 px-4 py-2 dark:border-zinc-800"
	>
		<h2 class="text-sm font-semibold text-zinc-600 dark:text-zinc-400">
			Version History ({versions.length})
		</h2>
	</div>

	<div class="flex-1 overflow-y-auto">
		{#if loading}
			<div class="flex items-center justify-center p-4">
				<span class="text-sm text-zinc-400">Loading history...</span>
			</div>
		{:else if error}
			<div class="p-4 text-sm text-red-500">{error}</div>
		{:else if versions.length === 0}
			<div class="flex items-center justify-center p-6">
				<span class="text-sm text-zinc-400">No version history available</span>
			</div>
		{:else}
			<ul class="divide-y divide-zinc-100 dark:divide-zinc-800/50">
				{#each versions as version (version.commit_hash)}
					<li class="px-4 py-3">
						<div class="flex items-start justify-between gap-2">
							<div class="min-w-0 flex-1">
								<p class="truncate text-sm text-zinc-900 dark:text-zinc-100">
									{version.message || 'No message'}
								</p>
								<div
									class="mt-0.5 flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400"
								>
									<span>{version.author_name || 'Unknown'}</span>
									<span>&middot;</span>
									<span>{formatDate(version.commit_date)}</span>
									<span>{formatTime(version.commit_date)}</span>
								</div>
							</div>
							{#if version.change_type}
								<span
									class="inline-flex shrink-0 items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium
                                    {version.change_type === 'created'
										? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
										: 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400'}"
								>
									{version.change_type}
								</span>
							{/if}
						</div>
						<code class="mt-1 block text-[10px] text-zinc-400"
							>{version.commit_hash.slice(0, 8)}</code
						>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>
