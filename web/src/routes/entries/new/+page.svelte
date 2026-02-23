<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import TemplatePicker from '$lib/components/entry/TemplatePicker.svelte';
	import Editor from '$lib/editor/Editor.svelte';
	import { api } from '$lib/api/client';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import type { TemplateSummary } from '$lib/api/types';

	let step = $state<'pick' | 'edit'>('pick');
	let templates = $state<TemplateSummary[]>([]);
	let loadingTemplates = $state(false);
	let title = $state('');
	let entryType = $state('note');
	let body = $state('');
	let saving = $state(false);

	const kb = $derived(kbStore.activeKB ?? '');

	onMount(async () => {
		if (!kb) await kbStore.load();
		loadTemplates();
	});

	async function loadTemplates() {
		if (!kb) return;
		loadingTemplates = true;
		try {
			const res = await api.getTemplates(kb);
			templates = res.templates;
		} catch {
			templates = [];
		} finally {
			loadingTemplates = false;
		}
	}

	async function onTemplateSelect(templateName: string | null) {
		if (templateName === null) {
			// Blank entry
			body = '';
			entryType = 'note';
			step = 'edit';
			return;
		}

		try {
			const rendered = await api.renderTemplate(kb, templateName, { title });
			body = rendered.body;
			entryType = rendered.entry_type;
			step = 'edit';
		} catch {
			uiStore.toast('Failed to load template', 'error');
		}
	}

	function onEditorChange(content: string) {
		body = content;
	}

	async function save() {
		if (!title.trim()) {
			uiStore.toast('Title is required', 'error');
			return;
		}
		saving = true;
		try {
			const res = await api.createEntry({
				kb,
				entry_type: entryType,
				title: title.trim(),
				body
			});
			uiStore.toast('Entry created', 'success');
			goto(`/entries/${res.id}`);
		} catch {
			uiStore.toast('Failed to create entry', 'error');
		} finally {
			saving = false;
		}
	}

	const breadcrumbs = [{ label: 'Entries', href: '/entries' }, { label: 'New Entry' }];
</script>

<Topbar {breadcrumbs} />

<div class="flex-1 overflow-y-auto p-6">
	{#if step === 'pick'}
		<div class="mx-auto max-w-lg">
			<h1 class="mb-2 text-2xl font-bold">New Entry</h1>

			<!-- Title input -->
			<div class="mb-4">
				<label for="entry-title" class="mb-1 block text-sm font-medium">Title</label>
				<input
					id="entry-title"
					type="text"
					bind:value={title}
					placeholder="Entry title..."
					class="w-full rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-800"
				/>
			</div>

			<!-- Template picker -->
			<h2 class="mb-2 text-lg font-medium">Choose a template</h2>
			<TemplatePicker
				{templates}
				loading={loadingTemplates}
				onselect={onTemplateSelect}
			/>
		</div>
	{:else}
		<!-- Editor step -->
		<div class="mx-auto max-w-4xl">
			<div class="mb-4 flex items-center justify-between">
				<div>
					<button
						onclick={() => (step = 'pick')}
						class="text-sm text-blue-600 hover:underline"
					>
						&larr; Back to templates
					</button>
					<h1 class="text-xl font-bold">{title || 'Untitled'}</h1>
					<span class="text-sm text-zinc-500">Type: {entryType}</span>
				</div>
				<div class="flex items-center gap-2">
					<input
						type="text"
						bind:value={title}
						placeholder="Title..."
						class="rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-800"
					/>
					<button
						onclick={save}
						disabled={saving}
						class="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
					>
						{saving ? 'Saving...' : 'Create'}
					</button>
				</div>
			</div>
			<div class="h-[calc(100vh-14rem)]">
				<Editor content={body} onchange={onEditorChange} onsave={save} />
			</div>
		</div>
	{/if}
</div>
