<script lang="ts">
	import { api } from '$lib/api/client';
	import { kbStore } from '$lib/stores/kbs.svelte';

	interface Props {
		selectedDate: string;
		onselect: (date: string) => void;
	}

	let { selectedDate, onselect }: Props = $props();

	// Current month being displayed (YYYY-MM)
	let viewYear = $state(new Date().getFullYear());
	let viewMonth = $state(new Date().getMonth()); // 0-indexed

	// Dates that have notes (fetched from API)
	let noteDates = $state<Set<string>>(new Set());

	const today = new Date();
	const todayStr = formatDate(today);

	const DAY_HEADERS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

	function formatDate(d: Date): string {
		const y = d.getFullYear();
		const m = String(d.getMonth() + 1).padStart(2, '0');
		const day = String(d.getDate()).padStart(2, '0');
		return `${y}-${m}-${day}`;
	}

	function monthLabel(): string {
		const d = new Date(viewYear, viewMonth, 1);
		return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
	}

	function prevMonth() {
		if (viewMonth === 0) {
			viewMonth = 11;
			viewYear--;
		} else {
			viewMonth--;
		}
	}

	function nextMonth() {
		if (viewMonth === 11) {
			viewMonth = 0;
			viewYear++;
		} else {
			viewMonth++;
		}
	}

	interface CalendarDay {
		date: string;
		day: number;
		currentMonth: boolean;
	}

	function getCalendarDays(): CalendarDay[] {
		const firstDay = new Date(viewYear, viewMonth, 1);
		const startDow = firstDay.getDay(); // 0=Sun
		const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

		const days: CalendarDay[] = [];

		// Previous month filler days
		const prevMonthDays = new Date(viewYear, viewMonth, 0).getDate();
		for (let i = startDow - 1; i >= 0; i--) {
			const d = new Date(viewYear, viewMonth - 1, prevMonthDays - i);
			days.push({ date: formatDate(d), day: prevMonthDays - i, currentMonth: false });
		}

		// Current month days
		for (let d = 1; d <= daysInMonth; d++) {
			const dt = new Date(viewYear, viewMonth, d);
			days.push({ date: formatDate(dt), day: d, currentMonth: true });
		}

		// Next month filler days (fill to complete last week row)
		const remaining = 7 - (days.length % 7);
		if (remaining < 7) {
			for (let d = 1; d <= remaining; d++) {
				const dt = new Date(viewYear, viewMonth + 1, d);
				days.push({ date: formatDate(dt), day: d, currentMonth: false });
			}
		}

		return days;
	}

	let calendarDays = $derived(getCalendarDays());

	async function fetchNoteDates() {
		const kb = kbStore.activeKB;
		if (!kb) return;
		const monthStr = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}`;
		try {
			const res = await api.getDailyDates(kb, monthStr);
			noteDates = new Set(res.dates);
		} catch {
			noteDates = new Set();
		}
	}

	// Fetch note dates when month changes or KB changes
	$effect(() => {
		// Access reactive deps
		const _y = viewYear;
		const _m = viewMonth;
		const _kb = kbStore.activeKB;
		fetchNoteDates();
	});

	// When selectedDate changes, navigate calendar to that month
	$effect(() => {
		if (selectedDate) {
			const parts = selectedDate.split('-');
			if (parts.length === 3) {
				const y = parseInt(parts[0], 10);
				const m = parseInt(parts[1], 10) - 1;
				if (y !== viewYear || m !== viewMonth) {
					viewYear = y;
					viewMonth = m;
				}
			}
		}
	});
</script>

<div class="w-full rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
	<!-- Month navigation -->
	<div class="mb-2 flex items-center justify-between">
		<button
			onclick={prevMonth}
			class="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
			aria-label="Previous month"
		>
			<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
		</button>
		<span class="text-sm font-medium text-zinc-700 dark:text-zinc-200">{monthLabel()}</span>
		<button
			onclick={nextMonth}
			class="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
			aria-label="Next month"
		>
			<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
			</svg>
		</button>
	</div>

	<!-- Day headers -->
	<div class="grid grid-cols-7 gap-0 text-center">
		{#each DAY_HEADERS as header}
			<div class="pb-1 text-xs font-medium text-zinc-400 dark:text-zinc-500">{header}</div>
		{/each}
	</div>

	<!-- Days grid -->
	<div class="grid grid-cols-7 gap-0">
		{#each calendarDays as day}
			<button
				onclick={() => onselect(day.date)}
				class="relative flex h-8 w-full flex-col items-center justify-center rounded text-xs transition-colors
					{day.currentMonth ? 'text-zinc-700 dark:text-zinc-300' : 'text-zinc-300 dark:text-zinc-600'}
					{day.date === selectedDate ? 'bg-blue-600 text-white dark:bg-blue-500 dark:text-white' : ''}
					{day.date === todayStr && day.date !== selectedDate ? 'ring-1 ring-blue-500' : ''}
					{day.date !== selectedDate ? 'hover:bg-zinc-100 dark:hover:bg-zinc-800' : ''}"
			>
				<span>{day.day}</span>
				{#if noteDates.has(day.date)}
					<span
						class="absolute bottom-0.5 h-1 w-1 rounded-full
							{day.date === selectedDate ? 'bg-white' : 'bg-blue-500 dark:bg-blue-400'}"
					></span>
				{/if}
			</button>
		{/each}
	</div>
</div>
