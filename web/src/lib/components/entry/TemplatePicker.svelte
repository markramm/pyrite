<script lang="ts">
	import type { TemplateSummary } from '$lib/api/types';

	interface Props {
		templates: TemplateSummary[];
		loading?: boolean;
		onselect: (templateName: string | null) => void;
	}

	let { templates, loading = false, onselect }: Props = $props();

	const typeColors: Record<string, string> = {
		event: '#3b82f6',
		person: '#8b5cf6',
		organization: '#f59e0b',
		topic: '#10b981',
		note: '#6b7280',
		place: '#ef4444',
		source: '#06b6d4',
		document: '#84cc16',
		standard: '#f472b6',
		component: '#22d3ee',
		adr: '#a78bfa',
		backlog_item: '#fb923c',
		meeting: '#3b82f6',
		article: '#6b7280'
	};

	function getColor(type: string): string {
		return typeColors[type] || '#6b7280';
	}
</script>

<div class="grid grid-cols-1 gap-3 sm:grid-cols-2" data-testid="template-picker">
	{#if loading}
		<p class="col-span-full text-sm text-zinc-400">Loading templates...</p>
	{:else}
		<!-- Blank entry option -->
		<button
			type="button"
			onclick={() => onselect(null)}
			class="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-zinc-300 p-4 text-center transition-all hover:border-gold-500/50 hover:shadow-lg hover:shadow-gold-500/5 dark:border-zinc-600"
			data-testid="template-blank"
		>
			<svg
				class="mb-2 h-6 w-6 text-zinc-400"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				viewBox="0 0 24 24"
				aria-hidden="true"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
			</svg>
			<div class="font-medium text-zinc-700 dark:text-zinc-200">Blank Entry</div>
			<p class="mt-0.5 text-sm text-zinc-500">Start from scratch</p>
		</button>

		{#each templates as tpl (tpl.name)}
			<button
				type="button"
				onclick={() => onselect(tpl.name)}
				class="relative overflow-hidden rounded-lg border border-zinc-200 p-4 text-left transition-all hover:border-gold-500/50 hover:shadow-lg hover:shadow-gold-500/5 dark:border-zinc-700"
				style="border-left: 4px solid {getColor(tpl.entry_type)}"
				data-testid="template-option"
			>
				<!-- Header row: icon + name + type badge -->
				<div class="flex items-start justify-between gap-2">
					<div class="flex items-center gap-2">
						<span
							class="mt-0.5 h-3 w-3 flex-shrink-0 rounded-full"
							style="background-color: {getColor(tpl.entry_type)}"
							aria-hidden="true"
						></span>
						<span class="font-medium text-zinc-800 dark:text-zinc-100">{tpl.name}</span>
					</div>
					<span
						class="flex-shrink-0 rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
					>
						{tpl.entry_type}
					</span>
				</div>

				<!-- Description -->
				{#if tpl.description}
					<p class="mt-1.5 line-clamp-2 text-sm text-zinc-500 dark:text-zinc-400">
						{tpl.description}
					</p>
				{/if}

				<!-- Tags -->
				{#if tpl.tags?.length > 0}
					<div class="mt-2 flex flex-wrap gap-1">
						{#each tpl.tags as tag (tag)}
							<span
								class="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
							>
								{tag}
							</span>
						{/each}
					</div>
				{/if}
			</button>
		{/each}

		{#if templates.length === 0}
			<p class="col-span-full text-sm text-zinc-400">No templates available for this KB.</p>
		{/if}
	{/if}
</div>
