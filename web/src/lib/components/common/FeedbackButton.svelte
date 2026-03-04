<script lang="ts">
	function openFeedback() {
		const page = encodeURIComponent(window.location.pathname);
		const browser = encodeURIComponent(navigator.userAgent);
		const url = `https://github.com/markramm/pyrite/issues/new?title=Bug:+&body=**Page:** ${page}%0A**Browser:** ${browser}%0A%0A**Description:**%0A`;
		window.open(url, '_blank', 'noopener,noreferrer');
	}
</script>

<button
	onclick={openFeedback}
	class="fixed bottom-4 right-4 z-50 flex items-center gap-1.5 rounded-full bg-zinc-800/80 px-3 py-1.5 text-xs text-zinc-400 shadow-lg backdrop-blur-sm transition-colors hover:bg-zinc-700/90 hover:text-zinc-200 border border-zinc-700/50"
	title="Report a bug or give feedback"
>
	<svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
		<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
	</svg>
	Feedback
</button>
