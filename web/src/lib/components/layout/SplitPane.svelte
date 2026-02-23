<!--
  SplitPane: A resizable CSS Grid split pane with a draggable divider.
  Supports right and bottom panel positions.
  Persists split ratio to localStorage.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';
	import { onMount } from 'svelte';

	interface Props {
		open?: boolean;
		position?: 'right' | 'bottom';
		minSize?: number;
		children: Snippet;
		panel?: Snippet;
	}

	let { open = false, position = 'right', minSize = 200, children, panel }: Props = $props();

	const STORAGE_KEY = 'pyrite-split-ratio';
	const DEFAULT_RATIO = 0.7;

	let ratio = $state(DEFAULT_RATIO);
	let dragging = $state(false);
	let container: HTMLDivElement | undefined = $state();

	onMount(() => {
		const saved = localStorage.getItem(STORAGE_KEY);
		if (saved) {
			const parsed = parseFloat(saved);
			if (!isNaN(parsed) && parsed > 0.2 && parsed < 0.95) {
				ratio = parsed;
			}
		}
	});

	function onPointerDown(e: PointerEvent) {
		e.preventDefault();
		dragging = true;
		const target = e.currentTarget as HTMLElement;
		target.setPointerCapture(e.pointerId);
	}

	function onPointerMove(e: PointerEvent) {
		if (!dragging || !container) return;

		const rect = container.getBoundingClientRect();
		let newRatio: number;

		if (position === 'right') {
			newRatio = (e.clientX - rect.left) / rect.width;
		} else {
			newRatio = (e.clientY - rect.top) / rect.height;
		}

		const containerSize = position === 'right' ? rect.width : rect.height;
		const minRatio = minSize / containerSize;
		const maxRatio = 1 - minRatio;

		newRatio = Math.max(minRatio, Math.min(maxRatio, newRatio));
		ratio = newRatio;
	}

	function onPointerUp() {
		if (dragging) {
			dragging = false;
			localStorage.setItem(STORAGE_KEY, ratio.toString());
		}
	}

	const gridStyle = $derived.by(() => {
		if (!open) return '';
		if (position === 'right') {
			return `grid-template-columns: ${ratio}fr ${1 - ratio}fr`;
		}
		return `grid-template-rows: ${ratio}fr ${1 - ratio}fr`;
	});

	const isHorizontal = $derived(position === 'right');
</script>

<div
	bind:this={container}
	class="relative flex-1 overflow-hidden"
	class:grid={open}
	style={gridStyle}
	role="group"
>
	<!-- Main content -->
	<div class="min-h-0 min-w-0 overflow-hidden">
		{@render children()}
	</div>

	{#if open && panel}
		<!-- Drag handle -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="absolute z-10 {isHorizontal
				? 'inset-y-0 w-1 cursor-col-resize hover:w-1.5'
				: 'inset-x-0 h-1 cursor-row-resize hover:h-1.5'} bg-zinc-200 transition-all hover:bg-zinc-400 dark:bg-zinc-700 dark:hover:bg-zinc-500"
			class:bg-blue-500={dragging}
			class:dark:bg-blue-500={dragging}
			style={isHorizontal
				? `left: calc(${ratio * 100}% - 2px)`
				: `top: calc(${ratio * 100}% - 2px)`}
			onpointerdown={onPointerDown}
			onpointermove={onPointerMove}
			onpointerup={onPointerUp}
		></div>

		<!-- Panel content -->
		<div
			class="min-h-0 min-w-0 overflow-hidden border-zinc-200 dark:border-zinc-800 {isHorizontal
				? 'border-l'
				: 'border-t'}"
		>
			{@render panel()}
		</div>
	{/if}
</div>
