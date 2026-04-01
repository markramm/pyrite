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
	import type { TypeSchemaInfo } from '$lib/api/types';

	let step = $state<'pick' | 'edit'>('pick');
	let templates = $state<TemplateSummary[]>([]);
	let loadingTemplates = $state(false);
	let typeSchemas = $state<Record<string, TypeSchemaInfo>>({});
	let title = $state('');
	let entryType = $state('note');
	let body = $state('');
	let tags = $state('');
	let date = $state('');
	let importance = $state(5);
	let status = $state('');
	let customFields = $state<Record<string, string>>({});
	let saving = $state(false);

	const kb = $derived(kbStore.activeKB ?? '');
	const selectedTypeSchema = $derived(typeSchemas[entryType]);
	const typeFieldEntries = $derived(
		selectedTypeSchema
			? Object.entries(selectedTypeSchema.fields).filter(
					([name]) => !['date', 'importance', 'status', 'tags', 'links'].includes(name)
				)
			: []
	);

	// Sort types: common ones first, then alphabetical
	const sortedTypeNames = $derived(() => {
		const names = Object.keys(typeSchemas);
		const priority = ['note', 'event', 'person', 'organization', 'document', 'topic'];
		const top = priority.filter((n) => names.includes(n));
		const rest = names.filter((n) => !priority.includes(n)).sort();
		return [...top, ...rest];
	});

	onMount(async () => {
		if (!kb) await kbStore.load();
		loadTemplates();
		loadTypeSchemas();
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

	async function loadTypeSchemas() {
		if (!kb) return;
		try {
			const res = await api.getTypeSchemas(kb);
			typeSchemas = res.types;
		} catch {
			typeSchemas = {};
		}
	}

	async function onTemplateSelect(templateName: string | null) {
		if (templateName === null) {
			// Keep the user's type selection from the picker step
			body = '';
			customFields = {};
			step = 'edit';
			return;
		}

		try {
			const rendered = await api.renderTemplate(kb, templateName, { title });
			body = rendered.body;
			entryType = rendered.entry_type;
			customFields = {};
			step = 'edit';
		} catch {
			uiStore.toast('Failed to load template', 'error');
		}
	}

	function onTypeChange(newType: string) {
		entryType = newType;
		customFields = {};
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
			const req: Record<string, unknown> = {
				kb,
				entry_type: entryType,
				title: title.trim(),
				body
			};
			if (tags.trim())
				req.tags = tags
					.split(',')
					.map((t: string) => t.trim())
					.filter(Boolean);
			if (date) req.date = date;
			if (importance !== 5) req.importance = importance;
			if (status.trim()) req.status = status.trim();

			// Merge non-empty custom fields into metadata
			const meta: Record<string, unknown> = {};
			for (const [key, value] of Object.entries(customFields)) {
				if (value.trim()) {
					const schema = selectedTypeSchema?.fields[key];
					if (schema?.type === 'number') {
						meta[key] = Number(value) || 0;
					} else if (schema?.type === 'list') {
						meta[key] = value
							.split(',')
							.map((v) => v.trim())
							.filter(Boolean);
					} else if (schema?.type === 'checkbox') {
						meta[key] = value === 'true';
					} else {
						meta[key] = value;
					}
				}
			}
			if (Object.keys(meta).length > 0) req.metadata = meta;

			const res = await api.createEntry(req as any);
			uiStore.toast('Entry created', 'success');
			goto(`/entries/${res.id}`);
		} catch {
			uiStore.toast('Failed to create entry', 'error');
		} finally {
			saving = false;
		}
	}

	function fieldTypeToInputType(fieldType: string): string {
		switch (fieldType) {
			case 'number':
				return 'number';
			case 'date':
			case 'datetime':
				return 'date';
			case 'checkbox':
				return 'checkbox';
			default:
				return 'text';
		}
	}

	const breadcrumbs = [{ label: 'Entries', href: '/entries' }, { label: 'New Entry' }];
</script>

<svelte:head><title>New Entry — Pyrite</title></svelte:head>

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

			<!-- Type selector -->
			{#if Object.keys(typeSchemas).length > 0}
				<div class="mb-4">
					<label for="entry-type" class="mb-1 block text-sm font-medium">Entry Type</label>
					<select
						id="entry-type"
						bind:value={entryType}
						onchange={(e) => onTypeChange(e.currentTarget.value)}
						class="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
					>
						{#each sortedTypeNames() as typeName}
							<option value={typeName}>
								{typeName}{typeSchemas[typeName]?.description
									? ` — ${typeSchemas[typeName].description.slice(0, 60)}`
									: ''}
							</option>
						{/each}
					</select>
					{#if selectedTypeSchema?.description}
						<p class="mt-1 text-xs text-zinc-500">{selectedTypeSchema.description}</p>
					{/if}
				</div>
			{/if}

			<!-- Template picker -->
			<h2 class="mb-2 text-lg font-medium">Choose a template</h2>
			<TemplatePicker {templates} loading={loadingTemplates} onselect={onTemplateSelect} />
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
						&larr; Back
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

			<!-- Type-specific fields + standard fields -->
			<div class="mb-4 space-y-3">
				<!-- Standard fields row -->
				<div class="grid grid-cols-2 gap-3 rounded-lg border border-zinc-200 p-3 dark:border-zinc-700 sm:grid-cols-4">
					<div>
						<label
							for="entry-tags"
							class="mb-1 block text-xs font-medium text-zinc-500">Tags</label
						>
						<input
							id="entry-tags"
							type="text"
							bind:value={tags}
							placeholder="tag1, tag2"
							class="w-full rounded border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-800"
						/>
					</div>
					<div>
						<label
							for="entry-date"
							class="mb-1 block text-xs font-medium text-zinc-500">Date</label
						>
						<input
							id="entry-date"
							type="date"
							bind:value={date}
							class="w-full rounded border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-800"
						/>
					</div>
					<div>
						<label
							for="entry-importance"
							class="mb-1 block text-xs font-medium text-zinc-500"
							>Importance: {importance}</label
						>
						<input
							id="entry-importance"
							type="range"
							min="1"
							max="10"
							bind:value={importance}
							class="w-full"
						/>
					</div>
					<div>
						<label
							for="entry-status"
							class="mb-1 block text-xs font-medium text-zinc-500">Status</label
						>
						<input
							id="entry-status"
							type="text"
							bind:value={status}
							placeholder="draft"
							class="w-full rounded border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-800"
						/>
					</div>
				</div>

				<!-- Type-specific fields -->
				{#if typeFieldEntries.length > 0}
					<div
						class="rounded-lg border border-purple-200 bg-purple-50/50 p-3 dark:border-purple-800 dark:bg-purple-900/10"
					>
						<p
							class="mb-2 text-xs font-semibold uppercase text-purple-600 dark:text-purple-400"
						>
							{entryType} fields
						</p>
						<div class="grid grid-cols-2 gap-3">
							{#each typeFieldEntries as [fieldName, fieldSchema]}
								<div>
									<label
										for="field-{fieldName}"
										class="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400"
									>
										{fieldName.replace(/_/g, ' ')}
										{#if fieldSchema.required}<span class="text-red-500">*</span
											>{/if}
									</label>
									{#if fieldSchema.options && fieldSchema.options.length > 0}
										<select
											id="field-{fieldName}"
											value={customFields[fieldName] ?? ''}
											onchange={(e) =>
												(customFields[fieldName] = e.currentTarget.value)}
											class="w-full rounded border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-800"
										>
											<option value="">Select...</option>
											{#each fieldSchema.options as opt}
												<option value={opt}>{opt}</option>
											{/each}
										</select>
									{:else if fieldSchema.type === 'list'}
										<input
											id="field-{fieldName}"
											type="text"
											value={customFields[fieldName] ?? ''}
											onchange={(e) =>
												(customFields[fieldName] = e.currentTarget.value)}
											placeholder="Comma-separated values"
											class="w-full rounded border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-800"
										/>
									{:else}
										<input
											id="field-{fieldName}"
											type={fieldTypeToInputType(fieldSchema.type)}
											value={customFields[fieldName] ?? ''}
											onchange={(e) =>
												(customFields[fieldName] = e.currentTarget.value)}
											placeholder={fieldSchema.description || ''}
											class="w-full rounded border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-800"
										/>
									{/if}
									{#if fieldSchema.description}
										<p class="mt-0.5 text-[10px] text-zinc-400">
											{fieldSchema.description}
										</p>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>

			<div class="h-[calc(100vh-20rem)]">
				<Editor content={body} onchange={onEditorChange} onsave={save} />
			</div>
		</div>
	{/if}
</div>
