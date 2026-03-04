<script lang="ts">
	interface Props {
		message: string;
		onretry?: () => void;
	}
	let { message, onretry }: Props = $props();

	let detailsOpen = $state(false);

	function reportIssueUrl(): string {
		const errorText = encodeURIComponent(message);
		const page = typeof window !== 'undefined' ? encodeURIComponent(window.location.pathname) : '';
		return `https://github.com/markramm/pyrite/issues/new?title=Bug:+Error+on+page&body=**Page:** ${page}%0A**Error:** ${errorText}%0A%0A**Steps to reproduce:**%0A1. %0A`;
	}
</script>

<div class="flex flex-col items-center justify-center py-16 text-center">
	<!-- Red exclamation circle icon (SVG, ~48px) -->
	<svg class="mb-4 h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
		<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
	</svg>
	<p class="mb-1 text-lg font-medium text-zinc-300">Something went wrong</p>
	<p class="mb-4 max-w-md text-sm text-zinc-500">{message}</p>

	<div class="flex items-center gap-3">
		{#if onretry}
			<button
				onclick={onretry}
				class="rounded-md border border-zinc-600 px-4 py-2 text-sm font-medium text-zinc-300 transition-colors hover:border-zinc-400 hover:text-zinc-100"
			>
				Try Again
			</button>
		{/if}
		<a
			href={reportIssueUrl()}
			target="_blank"
			rel="noopener noreferrer"
			class="rounded-md border border-zinc-700 px-4 py-2 text-sm text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200"
		>
			Report this issue
		</a>
	</div>

	<!-- Collapsible error details -->
	<div class="mt-6 w-full max-w-md">
		<button
			onclick={() => (detailsOpen = !detailsOpen)}
			class="flex items-center gap-1 text-xs text-zinc-600 transition-colors hover:text-zinc-400"
		>
			<svg
				class="h-3 w-3 transition-transform {detailsOpen ? 'rotate-90' : ''}"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
			</svg>
			Error details
		</button>
		{#if detailsOpen}
			<pre class="mt-2 max-h-40 overflow-auto rounded-md bg-zinc-800/50 p-3 text-left text-xs text-zinc-500 border border-zinc-700/50">{message}</pre>
		{/if}
	</div>
</div>
