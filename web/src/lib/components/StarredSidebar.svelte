<!--
  StarredSidebar: Displays starred entries in the sidebar.
  Shows above recent entries list.
-->
<script lang="ts">
	import { useStarred } from '$lib/stores/starred.svelte';

	const store = useStarred();

	$effect(() => {
		store.load();
	});
</script>

{#if store.starred.length > 0}
	<section class="mb-6">
		<h3 class="mb-2 flex items-center gap-1 text-sm font-semibold text-gray-600 dark:text-gray-400">
			<span class="text-yellow-500">&#9733;</span>
			Starred
			<span class="text-xs text-gray-400">({store.starred.length})</span>
		</h3>
		<ul class="space-y-1">
			{#each store.starred as item (item.entry_id + ':' + item.kb_name)}
				<li>
					<a
						href="/entries/{item.entry_id}?kb={item.kb_name}"
						class="block truncate rounded px-2 py-1 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
					>
						{item.entry_id}
					</a>
				</li>
			{/each}
		</ul>
	</section>
{/if}

{#if store.loading}
	<p class="px-2 text-xs text-gray-400">Loading starred...</p>
{/if}

{#if store.error}
	<p class="px-2 text-xs text-red-500">{store.error}</p>
{/if}
