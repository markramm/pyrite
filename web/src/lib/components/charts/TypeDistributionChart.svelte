<script lang="ts">
	const typeColors: Record<string, string> = {
		event: '#3b82f6',
		person: '#8b5cf6',
		organization: '#f59e0b',
		topic: '#10b981',
		note: '#6b7280',
		place: '#ef4444',
		source: '#06b6d4',
		document: '#84cc16',
		standard: '#f472b6',
		component: '#22d3ee',
		adr: '#a78bfa',
		backlog_item: '#fb923c',
		actor: '#6b7280',
		cascade_org: '#f59e0b',
	};

	const DEFAULT_COLOR = '#94a3b8';

	interface TypeCount {
		entry_type: string;
		count: number;
	}

	let { data }: { data: TypeCount[] } = $props();

	const total = $derived(data.reduce((sum, d) => sum + d.count, 0));

	// SVG donut geometry
	const cx = 100;
	const cy = 100;
	const r = 70;
	const strokeWidth = 28;
	const circumference = $derived(2 * Math.PI * r);

	interface Segment {
		entry_type: string;
		count: number;
		color: string;
		dasharray: string;
		dashoffset: number;
	}

	const segments: Segment[] = $derived.by(() => {
		if (total === 0) return [];
		let offset = 0;
		// Start at top (-90 deg) by offsetting first segment by circumference/4
		const quarterCirc = circumference / 4;
		return data.map((d) => {
			const fraction = d.count / total;
			const dash = fraction * circumference;
			const gap = circumference - dash;
			const seg: Segment = {
				entry_type: d.entry_type,
				count: d.count,
				color: typeColors[d.entry_type] ?? DEFAULT_COLOR,
				dasharray: `${dash} ${gap}`,
				// Offset: circumference/4 rotates start to top, then add cumulative offset
				dashoffset: quarterCirc - offset,
			};
			offset += dash;
			return seg;
		});
	});
</script>

{#if total === 0}
	<p class="text-sm text-zinc-400">No entries</p>
{:else}
	<div class="flex flex-col items-center gap-4">
		<!-- Donut SVG -->
		<svg width="200" height="200" viewBox="0 0 200 200" role="img" aria-label="Entry type distribution donut chart">
			<!-- Background ring -->
			<circle
				cx={cx}
				cy={cy}
				r={r}
				fill="none"
				stroke="currentColor"
				stroke-width={strokeWidth}
				class="text-zinc-100 dark:text-zinc-800"
			/>
			<!-- Segments -->
			{#each segments as seg}
				<circle
					cx={cx}
					cy={cy}
					r={r}
					fill="none"
					stroke={seg.color}
					stroke-width={strokeWidth}
					stroke-dasharray={seg.dasharray}
					stroke-dashoffset={seg.dashoffset}
					class="transition-all duration-300"
				/>
			{/each}
			<!-- Center total -->
			<text x={cx} y={cy - 6} text-anchor="middle" class="fill-zinc-800 dark:fill-zinc-100" font-size="22" font-weight="700">{total}</text>
			<text x={cx} y={cy + 14} text-anchor="middle" class="fill-zinc-400" font-size="11">entries</text>
		</svg>

		<!-- Legend -->
		<div class="w-full space-y-1">
			{#each data as d}
				<div class="flex items-center justify-between gap-2">
					<div class="flex min-w-0 items-center gap-2">
						<span
							class="h-2.5 w-2.5 shrink-0 rounded-full"
							style="background-color: {typeColors[d.entry_type] ?? DEFAULT_COLOR}"
						></span>
						<span class="truncate text-sm text-zinc-700 dark:text-zinc-300">{d.entry_type}</span>
					</div>
					<span class="shrink-0 text-sm font-medium text-zinc-500">{d.count}</span>
				</div>
			{/each}
		</div>
	</div>
{/if}
