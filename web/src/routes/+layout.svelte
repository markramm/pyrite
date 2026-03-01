<script lang="ts">
	import '../app.css';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import Toast from '$lib/components/common/Toast.svelte';
	import QuickSwitcher from '$lib/components/QuickSwitcher.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import ChatSidebar from '$lib/components/ai/ChatSidebar.svelte';
	import KeyboardShortcutsModal from '$lib/components/common/KeyboardShortcutsModal.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { wsClient } from '$lib/api/websocket';
	import { entryStore } from '$lib/stores/entries.svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import { registerShortcut } from '$lib/utils/keyboard';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { fade } from 'svelte/transition';

	let { children } = $props();

	let shortcutsOpen = $state(false);

	const AUTH_ROUTES = ['/login', '/register'];

	onMount(() => {
		// Initialize auth before loading KBs
		authStore.init().then(() => {
			const path = $page.url.pathname;
			const isAuthRoute = AUTH_ROUTES.includes(path);

			if (authStore.authConfig.enabled && !authStore.isAuthenticated && !isAuthRoute) {
				goto('/login');
				return;
			}
			if (authStore.authConfig.enabled && authStore.isAuthenticated && isAuthRoute) {
				goto('/');
				return;
			}
		});

		kbStore.load();

		// WebSocket for multi-tab awareness
		wsClient.connect();
		const unregisterWS = wsClient.onEvent((event) => {
			if (event.type === 'entry_updated' || event.type === 'entry_deleted') {
				// If viewing the changed entry, auto-reload
				if (entryStore.current && entryStore.current.id === event.entry_id) {
					if (event.type === 'entry_updated') {
						entryStore.loadEntry(event.entry_id, event.kb_name);
						uiStore.toast(`"${event.entry_id}" was updated in another tab`, 'info');
					} else {
						uiStore.toast(`"${event.entry_id}" was deleted in another tab`, 'info');
					}
				}
			} else if (event.type === 'entry_created') {
				uiStore.toast(`New entry created: ${event.entry_id}`, 'info');
			} else if (event.type === 'kb_synced') {
				uiStore.toast('Knowledge base synced', 'info');
			}
		});

		// Global: Cmd+D / Ctrl+D navigates to today's daily note
		const unregisterDaily = registerShortcut('d', ['mod'], () => {
			goto('/daily');
		});

		// Global: Cmd+Shift+K toggles AI chat sidebar
		const unregisterChat = registerShortcut('k', ['mod', 'shift'], () => {
			uiStore.toggleChatPanel();
		});

		// Global: Cmd+/ toggles sidebar
		const unregisterSidebar = registerShortcut('/', ['mod'], () => {
			uiStore.toggleSidebar();
		});

		// Global: ? opens keyboard shortcuts overlay
		function handleQuestionMark(e: KeyboardEvent) {
			if (e.key !== '?') return;
			const target = e.target as HTMLElement;
			if (
				target.tagName === 'INPUT' ||
				target.tagName === 'TEXTAREA' ||
				target.isContentEditable
			) {
				return;
			}
			shortcutsOpen = !shortcutsOpen;
		}
		window.addEventListener('keydown', handleQuestionMark);

		return () => {
			wsClient.disconnect();
			unregisterWS();
			unregisterDaily();
			unregisterChat();
			unregisterSidebar();
			window.removeEventListener('keydown', handleQuestionMark);
		};
	});
</script>

{#if authStore.loading}
	<div class="flex h-screen items-center justify-center bg-zinc-900">
		<p class="text-zinc-400">Loading...</p>
	</div>
{:else if authStore.authConfig.enabled && !authStore.isAuthenticated && !AUTH_ROUTES.includes($page.url.pathname)}
	<div class="flex h-screen items-center justify-center bg-zinc-900">
		<p class="text-zinc-400">Redirecting to login...</p>
	</div>
{:else if AUTH_ROUTES.includes($page.url.pathname)}
	{@render children()}
{:else}
	<div class="flex h-screen overflow-hidden">
		<Sidebar />
		<main class="flex flex-1 flex-col overflow-hidden">
			{#key $page.url.pathname}
				<div class="flex-1 overflow-hidden" in:fade={{ duration: 150, delay: 50 }} out:fade={{ duration: 100 }}>
					{@render children()}
				</div>
			{/key}
		</main>
		{#if uiStore.chatPanelOpen}
			<ChatSidebar />
		{/if}
	</div>
{/if}

<Toast />
<QuickSwitcher />
<CommandPalette />
<KeyboardShortcutsModal open={shortcutsOpen} onclose={() => (shortcutsOpen = false)} />
