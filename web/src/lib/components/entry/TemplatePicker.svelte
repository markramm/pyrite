<script lang="ts">
	import type { TemplateSummary } from '$lib/api/types';

	interface Props {
		templates: TemplateSummary[];
		loading?: boolean;
		onselect: (templateName: string | null) => void;
	}

	let { templates, loading = false, onselect }: Props = $props();
</script>

<div class="space-y-2" data-testid="template-picker">
	{#if loading}
		<p class="text-sm text-zinc-400">Loading templates...</p>
	{:else}
		<!-- Blank entry option -->
		<button
			type="button"
			onclick={() => onselect(null)}
			class="w-full rounded-lg border border-zinc-200 p-3 text-left transition-colors hover:border-blue-400 hover:bg-blue-50 dark:border-zinc-700 dark:hover:border-blue-600 dark:hover:bg-blue-950"
			data-testid="template-blank"
		>
			<div class="font-medium">Blank Entry</div>
			<p class="mt-0.5 text-sm text-zinc-500">Start from scratch</p>
		</button>

		{#each templates as tpl (tpl.name)}
			<button
				type="button"
				onclick={() => onselect(tpl.name)}
				class="w-full rounded-lg border border-zinc-200 p-3 text-left transition-colors hover:border-blue-400 hover:bg-blue-50 dark:border-zinc-700 dark:hover:border-blue-600 dark:hover:bg-blue-950"
				data-testid="template-option"
			>
				<div class="flex items-center justify-between">
					<span class="font-medium">{tpl.name}</span>
					<span
						class="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-500 dark:bg-zinc-800"
					>
						{tpl.entry_type}
					</span>
				</div>
				{#if tpl.description}
					<p class="mt-0.5 text-sm text-zinc-500">{tpl.description}</p>
				{/if}
			</button>
		{/each}

		{#if templates.length === 0}
			<p class="text-sm text-zinc-400">No templates available for this KB.</p>
		{/if}
	{/if}
</div>
