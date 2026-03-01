<script lang="ts">
	import KBSwitcher from '$lib/components/common/KBSwitcher.svelte';
	import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
	import { entryStore } from '$lib/stores/entries.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { page } from '$app/stores';

	const navItems = [
		{ href: '/search', label: 'Search', icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' },
		{ href: '/', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
		{ href: '/entries', label: 'Entries', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
		{ href: '/collections', label: 'Collections', icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
		{ href: '/graph', label: 'Graph', icon: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1' },
		{ href: '/timeline', label: 'Timeline', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
		{ href: '/daily', label: 'Daily Notes', icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' },
		{ href: '/qa', label: 'QA', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' },
		{ href: '/settings', label: 'Settings', icon: 'M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93s.844.105 1.205-.137l.738-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.242.361-.303.81-.137 1.206.166.395.506.709.93.78l.893.148c.543.09.94.56.94 1.11v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.424.07-.764.384-.93.78-.166.396-.105.844.137 1.205l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.361-.242-.81-.303-1.206-.137-.395.166-.709.506-.78.93l-.148.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.78-.93-.396-.166-.844-.105-1.205.137l-.738.527a1.125 1.125 0 01-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.242-.361.303-.81.137-1.206-.166-.395-.506-.709-.93-.78l-.894-.148c-.542-.09-.94-.56-.94-1.11v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.764-.384.93-.78.166-.396.105-.844-.137-1.205l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.361.242.81.303 1.206.137.395-.166.709-.506.78-.93l.148-.894zM15 12a3 3 0 11-6 0 3 3 0 016 0z' },
	];

	function isActive(href: string): boolean {
		const currentPath = $page.url.pathname;
		if (href === '/') {
			return currentPath === '/';
		}
		return currentPath.startsWith(href);
	}

	function handleNavClick() {
		if (typeof window !== 'undefined' && window.innerWidth < 1024) {
			uiStore.sidebarOpen = false;
		}
	}
</script>

<!-- Mobile overlay backdrop -->
{#if uiStore.sidebarOpen}
	<div
		class="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
		onclick={() => uiStore.toggleSidebar()}
		role="presentation"
	></div>
{/if}

<aside
	class="flex h-full w-64 flex-col border-r border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900
		fixed inset-y-0 left-0 z-50 transform transition-transform duration-200 ease-in-out
		lg:static lg:translate-x-0 lg:transform-none lg:transition-none
		{uiStore.sidebarOpen ? 'translate-x-0' : '-translate-x-full'}"
>
	<!-- Logo / Brand -->
	<div class="flex items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
		<a href="/" class="flex items-center gap-2">
			<span class="flex h-7 w-7 items-center justify-center rounded bg-gradient-to-br from-gold-400 to-gold-600 text-xs font-bold text-zinc-900">Py</span>
			<span class="font-display text-lg tracking-tight text-zinc-100">Pyrite</span>
		</a>
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
				onclick={handleNavClick}
				class="flex items-center gap-3 rounded-md px-3 py-2 text-sm {isActive(item.href)
					? 'bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-medium'
					: 'text-zinc-600 hover:bg-zinc-200 dark:text-zinc-400 dark:hover:bg-zinc-800'}"
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
					onclick={handleNavClick}
					class="block truncate rounded px-2 py-1 text-xs text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-800"
				>
					{id}
				</a>
			{/each}
		</div>
	{/if}
</aside>
