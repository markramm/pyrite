<script lang="ts">
	import { wsClient } from '$lib/api/websocket';
	import { onMount } from 'svelte';
	import { fade } from 'svelte/transition';

	let connected = $state(true);
	let showBanner = $state(false);
	let dismissedAt = $state(0);

	onMount(() => {
		connected = wsClient.connected;

		const unsub = wsClient.onStatusChange((status) => {
			connected = status;
			if (!status) {
				// Show banner after a short delay (avoid flash on page transitions)
				setTimeout(() => {
					if (!wsClient.connected) showBanner = true;
				}, 3000);
			} else {
				showBanner = false;
			}
		});

		return unsub;
	});

	function dismiss() {
		showBanner = false;
		dismissedAt = Date.now();
	}
</script>

{#if showBanner && !connected}
	<div
		class="fixed bottom-4 left-1/2 z-50 -translate-x-1/2"
		transition:fade={{ duration: 200 }}
	>
		<div class="flex items-center gap-3 rounded-lg border border-amber-500/30 bg-amber-950/90 px-4 py-2 text-sm text-amber-200 shadow-lg backdrop-blur-sm">
			<div class="h-2 w-2 animate-pulse rounded-full bg-amber-500"></div>
			<span>Connection lost — real-time updates paused</span>
			<button
				onclick={dismiss}
				class="ml-2 rounded px-1.5 py-0.5 text-amber-400 hover:bg-amber-900 hover:text-amber-200"
				aria-label="Dismiss"
			>
				&times;
			</button>
		</div>
	</div>
{/if}
