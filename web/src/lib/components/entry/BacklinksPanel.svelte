<!--
  BacklinksPanel: Shows entries that link to the current entry.
  Displayed in the split pane side panel on the entry detail page.
-->
<script lang="ts">
	interface Backlink {
		id: string;
		title: string;
		kb_name: string;
		entry_type: string;
		snippet?: string;
		note?: string;
		[key: string]: unknown;
	}

	interface Props {
		backlinks: Record<string, unknown>[];
		loading?: boolean;
	}

	let { backlinks, loading = false }: Props = $props();

	const items = $derived(backlinks as unknown as Backlink[]);
</script>

<div class="flex h-full flex-col overflow-hidden">
	<div
		class="flex items-center justify-between border-b border-zinc-200 px-4 py-2 dark:border-zinc-800"
	>
		<h2 class="text-sm font-semibold text-zinc-600 dark:text-zinc-400">
			Backlinks ({items.length})
		</h2>
	</div>

	<div class="flex-1 overflow-y-auto">
		{#if loading}
			<div class="flex items-center justify-center p-4">
				<span class="text-sm text-zinc-400">Loading backlinks...</span>
			</div>
		{:else if items.length === 0}
			<div class="flex items-center justify-center p-6">
				<span class="text-sm text-zinc-400">No entries link here yet</span>
			</div>
		{:else}
			<ul class="divide-y divide-zinc-100 dark:divide-zinc-800/50">
				{#each items as link (link.id + ':' + link.kb_name)}
					<li>
						<a
							href="/entries/{link.id}?kb={link.kb_name}"
							class="block px-4 py-3 hover:bg-zinc-100 dark:hover:bg-zinc-800"
						>
							<div class="flex items-start gap-2">
								<div class="min-w-0 flex-1">
									<div class="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
										{link.title || link.id}
									</div>
									{#if link.snippet}
										<p class="mt-0.5 line-clamp-2 text-xs text-zinc-500 dark:text-zinc-400">
											{link.snippet}
										</p>
									{/if}
								</div>
								<span
									class="inline-flex shrink-0 items-center rounded-full bg-zinc-100 px-1.5 py-0.5 text-[10px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
								>
									{link.entry_type}
								</span>
								{#if link.note}
									<span
										class="inline-flex shrink-0 items-center rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium text-blue-600 dark:bg-blue-900 dark:text-blue-400"
									>
										{link.note}
									</span>
								{/if}
							</div>
						</a>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>
