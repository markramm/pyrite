<script lang="ts">
	import { uiStore } from '$lib/stores/ui.svelte';
</script>

{#if uiStore.toasts.length > 0}
	<div class="fixed right-4 bottom-4 z-50 flex flex-col gap-2">
		{#each uiStore.toasts as toast (toast.id)}
			<div
				class="rounded-lg px-4 py-2 text-sm shadow-lg transition-all"
				class:bg-green-600={toast.type === 'success'}
				class:bg-red-600={toast.type === 'error'}
				class:bg-zinc-700={toast.type === 'info'}
				class:text-white={true}
			>
				{toast.message}
			</div>
		{/each}
	</div>
{/if}
