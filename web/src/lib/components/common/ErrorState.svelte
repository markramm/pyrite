<script lang="ts">
	interface Props {
		message: string;
		onretry?: () => void;
	}
	let { message, onretry }: Props = $props();
</script>

<div class="flex flex-col items-center justify-center py-16 text-center">
	<!-- Red exclamation circle icon (SVG, ~48px) -->
	<svg class="mb-4 h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
		<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
	</svg>
	<p class="mb-1 text-lg font-medium text-zinc-300">Something went wrong</p>
	<p class="mb-4 max-w-md text-sm text-zinc-500">{message}</p>
	{#if onretry}
		<button
			onclick={onretry}
			class="rounded-md border border-zinc-600 px-4 py-2 text-sm font-medium text-zinc-300 transition-colors hover:border-zinc-400 hover:text-zinc-100"
		>
			Try Again
		</button>
	{/if}
</div>
