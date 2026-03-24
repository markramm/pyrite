<script lang="ts">
	import '../../app.css';

	let { children } = $props();
</script>

<div class="flex min-h-screen flex-col bg-white dark:bg-zinc-900">
	<header class="border-b border-zinc-200 bg-zinc-50 px-6 py-3 dark:border-zinc-800 dark:bg-zinc-900">
		<div class="mx-auto flex max-w-4xl items-center justify-between">
			<a href="/site" class="text-lg font-bold text-zinc-900 dark:text-zinc-100">
				Pyrite <span class="text-sm font-normal text-zinc-500">Knowledge Base</span>
			</a>
			<nav class="flex items-center gap-4 text-sm">
				<a href="/site" class="text-zinc-500 transition-colors hover:text-zinc-900 dark:hover:text-zinc-100">Home</a>
				<a href="/site/search" class="text-zinc-500 transition-colors hover:text-zinc-900 dark:hover:text-zinc-100">Search</a>
			</nav>
		</div>
	</header>

	<main class="mx-auto w-full max-w-4xl flex-1 px-6 py-8">
		{@render children()}
	</main>

	<footer class="border-t border-zinc-200 px-6 py-4 dark:border-zinc-800">
		<div class="mx-auto max-w-4xl text-center text-xs text-zinc-400">
			Powered by <a href="https://pyrite.wiki" class="underline hover:text-zinc-600">Pyrite</a> — Knowledge-as-Code
		</div>
	</footer>
</div>
