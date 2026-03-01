<script lang="ts">
	import { uiStore } from '$lib/stores/ui.svelte';
	import { fly, fade } from 'svelte/transition';

	const icons: Record<string, string> = {
		success: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
		error: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
		info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
	};
</script>

{#if uiStore.toasts.length > 0}
	<div class="fixed top-4 right-4 z-50 flex flex-col gap-2">
		{#each uiStore.toasts as toast (toast.id)}
			<div
				in:fly={{ x: 300, duration: 300 }}
				out:fade={{ duration: 200 }}
				class="relative overflow-hidden rounded-lg border px-4 py-3 text-sm shadow-xl backdrop-blur-sm
					{toast.type === 'success' ? 'border-green-500/30 bg-green-950/90 text-green-200' :
					 toast.type === 'error' ? 'border-red-500/30 bg-red-950/90 text-red-200' :
					 'border-zinc-600/30 bg-zinc-800/90 text-zinc-200'}"
			>
				<div class="flex items-center gap-2.5">
					<svg class="h-4 w-4 flex-shrink-0 {toast.type === 'success' ? 'text-green-400' : toast.type === 'error' ? 'text-red-400' : 'text-zinc-400'}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d={icons[toast.type]} />
					</svg>
					<span>{toast.message}</span>
				</div>
				<div class="absolute bottom-0 left-0 h-0.5 animate-shrink {toast.type === 'success' ? 'bg-green-400' : toast.type === 'error' ? 'bg-red-400' : 'bg-zinc-400'}"></div>
			</div>
		{/each}
	</div>
{/if}

<style>
	@keyframes shrink {
		from { width: 100%; }
		to { width: 0%; }
	}
	.animate-shrink {
		animation: shrink 3s linear forwards;
	}
</style>
