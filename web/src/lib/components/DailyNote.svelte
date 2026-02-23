<script lang="ts">
	import Editor from '$lib/editor/Editor.svelte';
	import { api } from '$lib/api/client';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import type { EntryResponse } from '$lib/api/types';
	import { marked } from 'marked';

	interface Props {
		selectedDate: string;
		onnavigate: (date: string) => void;
	}

	let { selectedDate, onnavigate }: Props = $props();

	let entry = $state<EntryResponse | null>(null);
	let loading = $state(false);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let editing = $state(false);
	let editorContent = $state('');

	function formatDisplayDate(dateStr: string): string {
		const d = new Date(dateStr + 'T00:00:00');
		return d.toLocaleDateString('en-US', {
			weekday: 'long',
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}

	function prevDay() {
		const d = new Date(selectedDate + 'T00:00:00');
		d.setDate(d.getDate() - 1);
		const y = d.getFullYear();
		const m = String(d.getMonth() + 1).padStart(2, '0');
		const day = String(d.getDate()).padStart(2, '0');
		onnavigate(`${y}-${m}-${day}`);
	}

	function nextDay() {
		const d = new Date(selectedDate + 'T00:00:00');
		d.setDate(d.getDate() + 1);
		const y = d.getFullYear();
		const m = String(d.getMonth() + 1).padStart(2, '0');
		const day = String(d.getDate()).padStart(2, '0');
		onnavigate(`${y}-${m}-${day}`);
	}

	function goToToday() {
		const now = new Date();
		const y = now.getFullYear();
		const m = String(now.getMonth() + 1).padStart(2, '0');
		const day = String(now.getDate()).padStart(2, '0');
		onnavigate(`${y}-${m}-${day}`);
	}

	async function loadDailyNote() {
		const kb = kbStore.activeKB;
		if (!kb) {
			error = 'No KB selected';
			return;
		}
		loading = true;
		error = null;
		try {
			entry = await api.getDailyNote(selectedDate, kb);
			editorContent = entry.body ?? '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load daily note';
			entry = null;
		} finally {
			loading = false;
		}
	}

	function toggleEdit() {
		editing = !editing;
		if (editing && entry) {
			editorContent = entry.body ?? '';
		}
	}

	function onEditorChange(content: string) {
		editorContent = content;
	}

	async function save() {
		if (!entry || !kbStore.activeKB) return;
		saving = true;
		try {
			await api.updateEntry(entry.id, {
				kb: kbStore.activeKB,
				body: editorContent
			});
			// Reload to get server-side updates
			await loadDailyNote();
			uiStore.toast('Saved', 'success');
		} catch {
			uiStore.toast('Failed to save', 'error');
		} finally {
			saving = false;
		}
	}

	function renderMarkdown(md: string): string {
		return marked.parse(md, { async: false }) as string;
	}

	// Load daily note when date or KB changes
	$effect(() => {
		const _date = selectedDate;
		const _kb = kbStore.activeKB;
		if (_date && _kb) {
			editing = false;
			loadDailyNote();
		}
	});
</script>

<div class="flex flex-1 flex-col overflow-hidden">
	<!-- Date header and navigation -->
	<div class="flex items-center justify-between border-b border-zinc-200 px-6 py-3 dark:border-zinc-800">
		<div class="flex items-center gap-3">
			<button
				onclick={prevDay}
				class="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
				aria-label="Previous day"
			>
				<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
			</button>
			<div>
				<h1 class="text-lg font-bold text-zinc-800 dark:text-zinc-100">
					{formatDisplayDate(selectedDate)}
				</h1>
			</div>
			<button
				onclick={nextDay}
				class="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
				aria-label="Next day"
			>
				<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
				</svg>
			</button>
			<button
				onclick={goToToday}
				class="ml-2 rounded border border-zinc-300 px-2 py-0.5 text-xs text-zinc-500 hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-400 dark:hover:bg-zinc-800"
			>
				Today
			</button>
		</div>
		<div class="flex items-center gap-2">
			{#if editing}
				<button
					onclick={save}
					disabled={saving}
					class="rounded-md bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
				>
					{saving ? 'Saving...' : 'Save'}
				</button>
			{/if}
			{#if entry}
				<button
					onclick={toggleEdit}
					class="rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-600"
				>
					{editing ? 'View' : 'Edit'}
				</button>
			{/if}
		</div>
	</div>

	<!-- Content area -->
	<div class="flex-1 overflow-y-auto">
		{#if loading}
			<div class="flex h-full items-center justify-center">
				<span class="text-zinc-400">Loading...</span>
			</div>
		{:else if error}
			<div class="flex h-full items-center justify-center text-red-500">{error}</div>
		{:else if entry}
			<div class="h-full p-6">
				{#if editing}
					<div class="h-[calc(100vh-12rem)]">
						<Editor content={editorContent} onchange={onEditorChange} onsave={save} />
					</div>
				{:else}
					<div class="prose dark:prose-invert max-w-none">
						{@html renderMarkdown(entry.body ?? '')}
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
