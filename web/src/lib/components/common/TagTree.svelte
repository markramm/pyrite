<!--
  TagTree: Collapsible hierarchical tag browser.
  Displays tags organized by / separators in a tree view.
-->
<script lang="ts">
	import type { TagTreeNode } from '$lib/api/types';

	interface Props {
		nodes: TagTreeNode[];
		onSelect?: (fullPath: string) => void;
		depth?: number;
	}

	let { nodes, onSelect, depth = 0 }: Props = $props();
</script>

<ul class="space-y-0.5 {depth > 0 ? 'ml-4' : ''}">
	{#each nodes as node (node.full_path)}
		{@const hasChildren = node.children.length > 0}
		<li>
			<div class="flex items-center gap-1">
				{#if hasChildren}
					<details class="w-full">
						<summary
							class="flex cursor-pointer items-center gap-1 rounded px-1.5 py-0.5 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800"
						>
							<span class="text-zinc-700 dark:text-zinc-300">{node.name}</span>
							{#if node.count > 0}
								<span class="text-xs text-zinc-400">({node.count})</span>
							{/if}
						</summary>
						<svelte:self nodes={node.children} {onSelect} depth={depth + 1} />
					</details>
				{:else}
					<button
						onclick={() => onSelect?.(node.full_path)}
						class="flex w-full items-center gap-1 rounded px-1.5 py-0.5 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800"
					>
						<span class="text-zinc-700 dark:text-zinc-300">{node.name}</span>
						{#if node.count > 0}
							<span class="text-xs text-zinc-400">({node.count})</span>
						{/if}
					</button>
				{/if}
			</div>
		</li>
	{/each}
</ul>
