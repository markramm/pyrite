<script lang="ts">
	import type { TemplateSummary } from '$lib/api/types';
	import { typeColor } from '$lib/constants';

	interface Props {
		templates: TemplateSummary[];
		loading?: boolean;
		onselect: (templateName: string | null) => void;
	}

	let { templates, loading = false, onselect }: Props = $props();
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
				style="border-left: 4px solid {typeColor(tpl.entry_type)}"
				data-testid="template-option"
			>
				<!-- Header row: icon + name + type badge -->
				<div class="flex items-start justify-between gap-2">
					<div class="flex items-center gap-2">
						<span
							class="mt-0.5 h-3 w-3 flex-shrink-0 rounded-full"
							style="background-color: {typeColor(tpl.entry_type)}"
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

			</button>
		{/each}

		{#if templates.length === 0}
			<p class="col-span-full text-sm text-zinc-400">No templates available for this KB.</p>
		{/if}
	{/if}
</div>
