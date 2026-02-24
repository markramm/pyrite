<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import EntryMeta from '$lib/components/entry/EntryMeta.svelte';
	import BacklinksPanel from '$lib/components/entry/BacklinksPanel.svelte';
	import SplitPane from '$lib/components/layout/SplitPane.svelte';
	import Editor from '$lib/editor/Editor.svelte';
	import OutlinePanel from '$lib/components/entry/OutlinePanel.svelte';
	import { entryStore } from '$lib/stores/entries.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	let editing = $state(false);
	let editorContent = $state('');

	const entryId = $derived($page.params.id);

	onMount(() => {
		entryStore.loadEntry(entryId);

		function handleKeydown(e: KeyboardEvent) {
			if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'B') {
				e.preventDefault();
				uiStore.toggleBacklinksPanel();
			}
			if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'O') {
				e.preventDefault();
				uiStore.toggleOutlinePanel();
			}
		}
		window.addEventListener('keydown', handleKeydown);
		return () => window.removeEventListener('keydown', handleKeydown);
	});

	// Sync editor content when entry loads
	$effect(() => {
		if (entryStore.current) {
			editorContent = entryStore.current.body ?? '';
		}
	});

	function toggleEdit() {
		editing = !editing;
		if (editing && entryStore.current) {
			editorContent = entryStore.current.body ?? '';
		}
	}

	function onEditorChange(content: string) {
		editorContent = content;
		entryStore.markDirty();
	}

	async function save() {
		if (!entryStore.current) return;
		try {
			await entryStore.save(entryStore.current.id, entryStore.current.kb_name, {
				body: editorContent
			});
			uiStore.toast('Saved', 'success');
		} catch {
			uiStore.toast('Failed to save', 'error');
		}
	}

	const breadcrumbs = $derived([
		{ label: 'Entries', href: '/entries' },
		{ label: entryStore.current?.title ?? entryId }
	]);
</script>

<Topbar {breadcrumbs} />

<div class="flex flex-1 overflow-hidden">
	{#if entryStore.loading}
		<div class="flex flex-1 items-center justify-center">
			<span class="text-zinc-400">Loading...</span>
		</div>
	{:else if entryStore.error}
		<div class="flex flex-1 items-center justify-center text-red-500">{entryStore.error}</div>
	{:else if entryStore.current}
		<SplitPane open={uiStore.backlinksPanelOpen}>
			{#snippet children()}
				<div class="flex h-full overflow-hidden">
					<!-- Main content -->
					<div class="flex-1 overflow-y-auto">
						<!-- Toolbar -->
						<div class="flex items-center justify-between border-b border-zinc-200 px-6 py-2 dark:border-zinc-800">
							<h1 class="text-xl font-bold">{entryStore.current?.title}</h1>
							<div class="flex items-center gap-2">
								{#if editing}
									<button
										onclick={save}
										disabled={entryStore.saving}
										class="rounded-md bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
									>
										{entryStore.saving ? 'Saving...' : 'Save'}
									</button>
								{/if}
								<button
									onclick={toggleEdit}
									class="rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-600"
								>
									{editing ? 'View' : 'Edit'}
								</button>
								<button
									onclick={() => uiStore.toggleOutlinePanel()}
									class="rounded-md border px-3 py-1 text-sm {uiStore.outlinePanelOpen
										? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
										: 'border-zinc-300 dark:border-zinc-600'}"
									title="Toggle outline panel (Cmd+Shift+O)"
								>
									Outline
								</button>
								<button
									onclick={() => uiStore.toggleBacklinksPanel()}
									class="rounded-md border px-3 py-1 text-sm {uiStore.backlinksPanelOpen
										? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
										: 'border-zinc-300 dark:border-zinc-600'}"
									title="Toggle backlinks panel (Cmd+Shift+B)"
								>
									Backlinks
								</button>
							</div>
						</div>

						<!-- Editor or rendered view -->
						<div class="flex h-full flex-1 overflow-hidden">
							{#if uiStore.outlinePanelOpen && !editing}
								<aside class="w-56 shrink-0 overflow-y-auto border-r border-zinc-200 dark:border-zinc-800">
									<OutlinePanel body={entryStore.current?.body ?? ''} />
								</aside>
							{/if}
							<div class="flex-1 overflow-y-auto p-6">
								{#if editing}
									<div class="h-[calc(100vh-12rem)]">
										<Editor content={editorContent} onchange={onEditorChange} onsave={save} />
									</div>
								{:else}
									<div class="prose dark:prose-invert max-w-none">
										{@html renderMarkdown(entryStore.current?.body ?? '')}
									</div>
								{/if}
							</div>
						</div>
					</div>

					<!-- Metadata sidebar -->
					<aside class="w-64 shrink-0 overflow-y-auto border-l border-zinc-200 p-4 dark:border-zinc-800">
						{#if entryStore.current}
							<EntryMeta entry={entryStore.current} />
						{/if}
					</aside>
				</div>
			{/snippet}

			{#snippet panel()}
				<BacklinksPanel
					backlinks={entryStore.current?.backlinks ?? []}
					loading={entryStore.loading}
				/>
			{/snippet}
		</SplitPane>
	{/if}
</div>

<script lang="ts" module>
	import { marked } from 'marked';
	import { renderWikilinks } from '$lib/editor/wikilink-utils';
	import { renderCallouts } from '$lib/editor/callouts';

	// Custom renderer that adds id attributes to headings for outline scroll-to
	const renderer = new marked.Renderer();
	renderer.heading = ({ text, depth }: { text: string; depth: number }) => {
		const slug = text
			.toLowerCase()
			.replace(/<[^>]*>/g, '')
			.replace(/[^\w\s-]/g, '')
			.replace(/\s+/g, '-')
			.replace(/-+/g, '-')
			.trim();
		return `<h${depth} id="${slug}">${text}</h${depth}>`;
	};

	function renderMarkdown(md: string): string {
		let html = marked.parse(md, { async: false, renderer }) as string;
		html = renderCallouts(html);
		html = renderWikilinks(html);
		return html;
	}
</script>
