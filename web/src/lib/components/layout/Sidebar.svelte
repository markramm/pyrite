<script lang="ts">
	import KBSwitcher from '$lib/components/common/KBSwitcher.svelte';
	import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
	import { entryStore } from '$lib/stores/entries.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';

	const navItems = [
		{ href: '/', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
		{ href: '/entries', label: 'Entries', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
		{ href: '/graph', label: 'Graph', icon: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1' },
		{ href: '/timeline', label: 'Timeline', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
		{ href: '/daily', label: 'Daily Notes', icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' },
	];
</script>

<aside
	class="flex h-full w-64 flex-col border-r border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900"
	class:hidden={!uiStore.sidebarOpen}
>
	<!-- Logo / Brand -->
	<div class="flex items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
		<a href="/" class="text-lg font-bold tracking-tight">Pyrite</a>
		<ThemeToggle />
	</div>

	<!-- KB Switcher -->
	<div class="border-b border-zinc-200 px-3 py-2 dark:border-zinc-800">
		<KBSwitcher />
	</div>

	<!-- Navigation -->
	<nav class="flex-1 space-y-0.5 overflow-y-auto px-2 py-2">
		{#each navItems as item}
			<a
				href={item.href}
				class="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-600 hover:bg-zinc-200 dark:text-zinc-400 dark:hover:bg-zinc-800"
			>
				<svg class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={item.icon} />
				</svg>
				{item.label}
			</a>
		{/each}
	</nav>

	<!-- Recent Entries -->
	{#if entryStore.recentIds.length > 0}
		<div class="border-t border-zinc-200 px-3 py-2 dark:border-zinc-800">
			<p class="mb-1 text-xs font-medium uppercase tracking-wider text-zinc-500">Recent</p>
			{#each entryStore.recentIds.slice(0, 5) as id}
				<a
					href="/entries/{id}"
					class="block truncate rounded px-2 py-1 text-xs text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-800"
				>
					{id}
				</a>
			{/each}
		</div>
	{/if}
</aside>
