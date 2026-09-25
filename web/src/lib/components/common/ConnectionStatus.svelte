<script lang="ts">
	import { wsClient, type WSStatus } from '$lib/api/websocket';
	import { onMount } from 'svelte';
	import { fade } from 'svelte/transition';

	// Read from the client, not assumed: a refusal can land before mount.
	let status = $state<WSStatus>(wsClient.status);
	// A dropped connection shows only after a grace period (no flash on a
	// server restart); a refusal shows at once, since nothing will retry it.
	let lostLongEnough = $state(false);
	let dismissed = $state(false);

	let banner = $derived.by(() => {
		if (dismissed) return null;
		if (status === 'refused') return 'Real-time updates unavailable';
		if ((status === 'closed' || status === 'connecting') && lostLongEnough) {
			return 'Connection lost — real-time updates paused';
		}
		return null;
	});

	onMount(() => {
		let timer: ReturnType<typeof setTimeout> | null = null;

		const unsub = wsClient.onStatus((next) => {
			status = next;
			dismissed = false;
			if (next === 'closed') {
				if (timer === null) {
					timer = setTimeout(() => {
						timer = null;
						lostLongEnough = true;
					}, 3000);
				}
			} else if (next !== 'connecting') {
				// open, idle or refused: the loss (if any) is over.
				if (timer !== null) clearTimeout(timer);
				timer = null;
				lostLongEnough = false;
			}
		});

		return () => {
			unsub();
			if (timer !== null) clearTimeout(timer);
		};
	});

	function dismiss() {
		dismissed = true;
	}
</script>

{#if banner}
	<div
		class="fixed bottom-4 left-1/2 z-50 -translate-x-1/2"
		role="status"
		transition:fade={{ duration: 200 }}
	>
		<div class="flex items-center gap-3 rounded-lg border border-amber-500/30 bg-amber-950/90 px-4 py-2 text-sm text-amber-200 shadow-lg backdrop-blur-sm">
			<div class="h-2 w-2 animate-pulse rounded-full bg-amber-500"></div>
			<span>{banner}</span>
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
