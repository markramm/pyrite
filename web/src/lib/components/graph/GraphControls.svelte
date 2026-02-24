<script lang="ts">
	interface Props {
		kbs: string[];
		entryTypes: string[];
		selectedKb: string;
		selectedType: string;
		depth: number;
		selectedLayout: string;
		onKbChange: (kb: string) => void;
		onTypeChange: (type: string) => void;
		onDepthChange: (depth: number) => void;
		onResetLayout: () => void;
		onFit: () => void;
		onSearch: (query: string) => void;
		onLayoutChange: (layout: string) => void;
	}

	let {
		kbs,
		entryTypes,
		selectedKb,
		selectedType,
		depth,
		selectedLayout,
		onKbChange,
		onTypeChange,
		onDepthChange,
		onResetLayout,
		onFit,
		onSearch,
		onLayoutChange
	}: Props = $props();

	const layouts = [
		{ value: 'cose-bilkent', label: 'Force-directed' },
		{ value: 'circle', label: 'Circle' },
		{ value: 'grid', label: 'Grid' },
		{ value: 'concentric', label: 'Concentric' }
	];
</script>

<div class="flex flex-wrap items-center gap-3 rounded-lg border border-zinc-200 bg-white px-4 py-2 dark:border-zinc-800 dark:bg-zinc-900">
	<label class="flex items-center gap-1.5 text-sm text-zinc-400">
		KB
		<select
			class="rounded border border-zinc-300 bg-transparent px-2 py-1 text-sm dark:border-zinc-700"
			value={selectedKb}
			onchange={(e) => onKbChange((e.target as HTMLSelectElement).value)}
		>
			<option value="">All</option>
			{#each kbs as kb}
				<option value={kb}>{kb}</option>
			{/each}
		</select>
	</label>

	<label class="flex items-center gap-1.5 text-sm text-zinc-400">
		Type
		<select
			class="rounded border border-zinc-300 bg-transparent px-2 py-1 text-sm dark:border-zinc-700"
			value={selectedType}
			onchange={(e) => onTypeChange((e.target as HTMLSelectElement).value)}
		>
			<option value="">All</option>
			{#each entryTypes as t}
				<option value={t}>{t}</option>
			{/each}
		</select>
	</label>

	<label class="flex items-center gap-1.5 text-sm text-zinc-400">
		Depth
		<input
			type="range"
			min="1"
			max="3"
			value={depth}
			oninput={(e) => onDepthChange(Number((e.target as HTMLInputElement).value))}
			class="w-20"
		/>
		<span class="w-4 text-center text-sm text-zinc-300">{depth}</span>
	</label>

	<label class="flex items-center gap-1.5 text-sm text-zinc-400">
		Layout
		<select
			class="rounded border border-zinc-300 bg-transparent px-2 py-1 text-sm dark:border-zinc-700"
			value={selectedLayout}
			onchange={(e) => onLayoutChange((e.target as HTMLSelectElement).value)}
		>
			{#each layouts as l}
				<option value={l.value}>{l.label}</option>
			{/each}
		</select>
	</label>

	<input
		type="search"
		placeholder="Search nodes..."
		class="rounded border border-zinc-300 bg-transparent px-2 py-1 text-sm dark:border-zinc-700"
		oninput={(e) => onSearch((e.target as HTMLInputElement).value)}
	/>

	<div class="ml-auto flex gap-2">
		<button
			onclick={onFit}
			class="rounded border border-zinc-300 px-2 py-1 text-xs dark:border-zinc-700"
		>
			Fit
		</button>
		<button
			onclick={onResetLayout}
			class="rounded border border-zinc-300 px-2 py-1 text-xs dark:border-zinc-700"
		>
			Reset Layout
		</button>
	</div>
</div>
