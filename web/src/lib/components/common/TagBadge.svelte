<script lang="ts">
	interface Props {
		tag: string;
	}

	let { tag }: Props = $props();
</script>

<span class="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
	{tag}
</span>
