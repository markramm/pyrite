<script lang="ts">
	import { collectionStore } from '$lib/stores/collections.svelte';
</script>

<div class="flex rounded-md border border-zinc-300 dark:border-zinc-700">
	<button
		onclick={() => collectionStore.setViewMode('list')}
		class="px-2.5 py-1.5 text-sm {collectionStore.viewMode === 'list'
			? 'bg-zinc-200 dark:bg-zinc-700'
			: 'hover:bg-zinc-100 dark:hover:bg-zinc-800'}"
		title="List view"
	>
		<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
		</svg>
	</button>
	<button
		onclick={() => collectionStore.setViewMode('table')}
		class="border-l border-zinc-300 px-2.5 py-1.5 text-sm dark:border-zinc-700 {collectionStore.viewMode === 'table'
			? 'bg-zinc-200 dark:bg-zinc-700'
			: 'hover:bg-zinc-100 dark:hover:bg-zinc-800'}"
		title="Table view"
	>
		<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18M3 6h18M3 18h18M10 6v12M17 6v12" />
		</svg>
	</button>
	<button
		onclick={() => collectionStore.setViewMode('kanban')}
		class="border-l border-zinc-300 px-2.5 py-1.5 text-sm dark:border-zinc-700 {collectionStore.viewMode === 'kanban'
			? 'bg-zinc-200 dark:bg-zinc-700'
			: 'hover:bg-zinc-100 dark:hover:bg-zinc-800'}"
		title="Kanban view"
	>
		<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7" />
		</svg>
	</button>
	<button
		onclick={() => collectionStore.setViewMode('gallery')}
		class="border-l border-zinc-300 px-2.5 py-1.5 text-sm dark:border-zinc-700 {collectionStore.viewMode === 'gallery'
			? 'bg-zinc-200 dark:bg-zinc-700'
			: 'hover:bg-zinc-100 dark:hover:bg-zinc-800'}"
		title="Gallery view"
	>
		<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
		</svg>
	</button>
</div>
