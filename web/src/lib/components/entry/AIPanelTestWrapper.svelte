<script lang="ts">
	import AIPanel from './AIPanel.svelte';
	import type { Snippet } from 'svelte';

	let {
		entryId = 'test-entry',
		kbName = 'test-kb',
		entryTitle = 'Test Entry',
		tags = [] as string[],
		onTagsChanged = () => {},
	}: {
		entryId?: string;
		kbName?: string;
		entryTitle?: string;
		tags?: string[];
		onTagsChanged?: (tags: string[]) => void;
	} = $props();
</script>

<AIPanel
	{entryId}
	{kbName}
	{entryTitle}
	{tags}
	{onTagsChanged}
>
	{#snippet toolbar({ aiMenuButton })}
		<div data-testid="toolbar">
			{@render aiMenuButton()}
		</div>
	{/snippet}
</AIPanel>
