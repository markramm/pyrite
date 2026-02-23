<script lang="ts">
	import { kbStore } from '$lib/stores/kbs.svelte';
</script>

<select
	value={kbStore.activeKB ?? ''}
	onchange={(e) => kbStore.setActive(e.currentTarget.value)}
	class="w-full rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800"
>
	{#each kbStore.kbs as kb}
		<option value={kb.name}>{kb.name} ({kb.entries})</option>
	{/each}
</select>
