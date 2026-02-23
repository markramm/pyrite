<script lang="ts">
	import { entryStore } from '$lib/stores/entries.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';

	interface Props {
		title?: string;
		breadcrumbs?: { label: string; href?: string }[];
	}

	let { title = '', breadcrumbs = [] }: Props = $props();
</script>

<header class="flex h-12 items-center justify-between border-b border-zinc-200 px-4 dark:border-zinc-800">
	<div class="flex items-center gap-3">
		<!-- Sidebar toggle (mobile) -->
		<button
			onclick={() => uiStore.toggleSidebar()}
			class="rounded-md p-1 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 lg:hidden"
		>
			<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
			</svg>
		</button>

		<!-- Breadcrumbs -->
		<nav class="flex items-center gap-1 text-sm">
			{#each breadcrumbs as crumb, i}
				{#if i > 0}
					<span class="text-zinc-400">/</span>
				{/if}
				{#if crumb.href}
					<a href={crumb.href} class="text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300">
						{crumb.label}
					</a>
				{:else}
					<span class="text-zinc-700 dark:text-zinc-200">{crumb.label}</span>
				{/if}
			{/each}
			{#if title && breadcrumbs.length === 0}
				<span class="font-medium">{title}</span>
			{/if}
		</nav>
	</div>

	<div class="flex items-center gap-2">
		<!-- Save status -->
		{#if entryStore.saving}
			<span class="text-xs text-zinc-400">Saving...</span>
		{:else if entryStore.dirty}
			<span class="text-xs text-amber-500">Unsaved</span>
		{/if}
	</div>
</header>
