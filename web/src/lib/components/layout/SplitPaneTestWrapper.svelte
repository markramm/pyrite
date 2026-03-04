<script lang="ts">
	import SplitPane from './SplitPane.svelte';
	let { open = false, position = 'right', minSize = 200 }: { open?: boolean; position?: 'right' | 'bottom'; minSize?: number } = $props();
</script>
<SplitPane {open} {position} {minSize}>
	{#snippet children()}<div data-testid="main-content">Main</div>{/snippet}
	{#snippet panel()}<div data-testid="panel-content">Panel</div>{/snippet}
</SplitPane>
