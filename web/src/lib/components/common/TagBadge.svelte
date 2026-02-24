<script lang="ts">
	interface Props {
		tag: string;
		href?: string;
		onclick?: (e: MouseEvent) => void;
	}

	let { tag, href, onclick }: Props = $props();
</script>

{#if href}
	<a
		{href}
		onclick={onclick}
		class="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50"
	>
		{tag}
	</a>
{:else if onclick}
	<button
		onclick={onclick}
		class="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50"
	>
		{tag}
	</button>
{:else}
	<span class="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
		{tag}
	</span>
{/if}
