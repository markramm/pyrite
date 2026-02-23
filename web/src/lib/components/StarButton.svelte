<!--
  StarButton: Toggle star/unstar on an entry.
  Uses Svelte 5 runes and Tailwind CSS.
-->
<script lang="ts">
	import { useStarred } from '$lib/stores/starred.svelte';

	interface Props {
		entryId: string;
		kbName: string;
		size?: 'sm' | 'md' | 'lg';
	}

	let { entryId, kbName, size = 'md' }: Props = $props();

	const store = useStarred();
	let active = $derived(store.isStarred(entryId, kbName));

	const sizeClasses: Record<string, string> = {
		sm: 'text-base w-6 h-6',
		md: 'text-xl w-8 h-8',
		lg: 'text-2xl w-10 h-10'
	};

	async function toggle() {
		if (active) {
			await store.unstar(entryId, kbName);
		} else {
			await store.star(entryId, kbName);
		}
	}
</script>

<button
	onclick={toggle}
	class="inline-flex items-center justify-center rounded-md transition-colors hover:bg-gray-100 dark:hover:bg-gray-800 {sizeClasses[size]}"
	aria-label={active ? 'Unstar entry' : 'Star entry'}
	title={active ? 'Remove from starred' : 'Add to starred'}
>
	{#if active}
		<span class="text-yellow-500">&#9733;</span>
	{:else}
		<span class="text-gray-400 hover:text-yellow-400">&#9734;</span>
	{/if}
</button>
