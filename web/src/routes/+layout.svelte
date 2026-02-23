<script lang="ts">
	import '../app.css';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import Toast from '$lib/components/common/Toast.svelte';
	import QuickSwitcher from '$lib/components/QuickSwitcher.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { registerShortcut } from '$lib/utils/keyboard';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	let { children } = $props();

	onMount(() => {
		kbStore.load();

		// Global: Cmd+D / Ctrl+D navigates to today's daily note
		const unregisterDaily = registerShortcut('d', ['mod'], () => {
			goto('/daily');
		});

		return () => {
			unregisterDaily();
		};
	});
</script>

<div class="flex h-screen overflow-hidden">
	<Sidebar />
	<main class="flex flex-1 flex-col overflow-hidden">
		{@render children()}
	</main>
</div>

<Toast />
<QuickSwitcher />
<CommandPalette />
