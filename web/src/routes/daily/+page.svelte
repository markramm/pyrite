<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import DailyNote from '$lib/components/DailyNote.svelte';
	import Calendar from '$lib/components/Calendar.svelte';

	function todayStr(): string {
		const now = new Date();
		const y = now.getFullYear();
		const m = String(now.getMonth() + 1).padStart(2, '0');
		const d = String(now.getDate()).padStart(2, '0');
		return `${y}-${m}-${d}`;
	}

	let selectedDate = $state(todayStr());

	function navigateToDate(date: string) {
		selectedDate = date;
	}

	const breadcrumbs = $derived([
		{ label: 'Daily Notes', href: '/daily' },
		{ label: selectedDate }
	]);
</script>

<Topbar {breadcrumbs} />

<div class="flex flex-1 overflow-hidden">
	<!-- Main content area -->
	<DailyNote {selectedDate} onnavigate={navigateToDate} />

	<!-- Calendar sidebar -->
	<aside class="hidden w-64 shrink-0 overflow-y-auto border-l border-zinc-200 p-4 dark:border-zinc-800 md:block">
		<Calendar {selectedDate} onselect={navigateToDate} />
	</aside>
</div>
