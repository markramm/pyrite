<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import EntryMeta from '$lib/components/entry/EntryMeta.svelte';
	import BacklinksPanel from '$lib/components/entry/BacklinksPanel.svelte';
	import VersionHistoryPanel from '$lib/components/entry/VersionHistoryPanel.svelte';
	import LocalGraphPanel from '$lib/components/graph/LocalGraphPanel.svelte';
	import SplitPane from '$lib/components/layout/SplitPane.svelte';
	import Editor from '$lib/editor/Editor.svelte';
	import TiptapEditor from '$lib/editor/TiptapEditor.svelte';
	import OutlinePanel from '$lib/components/entry/OutlinePanel.svelte';
	import AIPanel from '$lib/components/entry/AIPanel.svelte';
	import { entryStore } from '$lib/stores/entries.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { api } from '$lib/api/client';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { parseWikilinks } from '$lib/editor/wikilink-utils';

	let editing = $state(false);
	let editorContent = $state('');
	let resolvedIds = $state<Set<string>>(new Set());

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
			if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'H') {
				e.preventDefault();
				uiStore.toggleVersionHistoryPanel();
			}
			if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'G') {
				e.preventDefault();
				uiStore.toggleLocalGraphPanel();
			}
		}
		window.addEventListener('keydown', handleKeydown);

		return () => {
			window.removeEventListener('keydown', handleKeydown);
		};
	});

	// Sync editor content and resolve wikilinks when entry loads
	$effect(() => {
		if (entryStore.current) {
			editorContent = entryStore.current.body ?? '';
			// Batch-resolve wikilink targets for red link rendering
			const body = entryStore.current.body ?? '';
			const links = parseWikilinks(body);
			if (links.length > 0) {
				const targets = [...new Set(links.map((l) => l.target))];
				api.resolveBatch(targets).then((res) => {
					const existing = new Set<string>();
					for (const [id, exists] of Object.entries(res.resolved)) {
						if (exists) existing.add(id);
					}
					resolvedIds = existing;
				}).catch(() => {
					// On failure, treat all as existing (no red links)
					resolvedIds = new Set();
				});
			} else {
				resolvedIds = new Set();
			}
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

	async function handleTagsChanged(newTags: string[]) {
		if (!entryStore.current) return;
		try {
			await entryStore.save(entryStore.current.id, entryStore.current.kb_name, {
				tags: newTags
			});
		} catch {
			uiStore.toast('Failed to add tag', 'error');
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
		<SplitPane open={uiStore.backlinksPanelOpen || uiStore.versionHistoryPanelOpen || uiStore.localGraphPanelOpen}>
			{#snippet children()}
				<div class="flex h-full overflow-hidden">
					<!-- Main content -->
					<div class="flex-1 overflow-y-auto">
						<!-- Toolbar + AI results -->
						<AIPanel
							entryId={entryStore.current?.id ?? ''}
							kbName={entryStore.current?.kb_name ?? ''}
							entryTitle={entryStore.current?.title ?? ''}
							tags={entryStore.current?.tags ?? []}
							onTagsChanged={handleTagsChanged}
						>
							{#snippet toolbar({ aiMenuButton })}
								<div class="flex items-center justify-between border-b border-zinc-200 px-6 py-2 dark:border-zinc-800">
									<h1 class="text-xl font-bold">{entryStore.current?.title}</h1>
									<div class="flex items-center gap-2">
										<!-- Group 1: Edit actions -->
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
										{#if editing}
											<button
												onclick={() => uiStore.toggleEditorMode()}
												class="rounded-md border px-3 py-1 text-sm {uiStore.editorMode === 'wysiwyg'
													? 'border-green-500 bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300'
													: 'border-zinc-300 dark:border-zinc-600'}"
												title="Toggle between source and rich text editing"
											>
												{uiStore.editorMode === 'source' ? 'Rich Text' : 'Source'}
											</button>
										{/if}

										<!-- Divider -->
										<div class="mx-1 h-5 w-px bg-zinc-300 dark:bg-zinc-700"></div>

										<!-- Group 2: AI menu -->
										{@render aiMenuButton()}

										<!-- Divider -->
										<div class="mx-1 h-5 w-px bg-zinc-300 dark:bg-zinc-700"></div>

										<!-- Group 3: Panel toggles (icon-only) -->
										<button
											onclick={() => uiStore.toggleOutlinePanel()}
											class="flex h-8 w-8 items-center justify-center rounded-md border {uiStore.outlinePanelOpen
												? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
												: 'border-zinc-300 dark:border-zinc-600'}"
											title="Toggle outline panel (Cmd+Shift+O)"
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
											</svg>
										</button>
										<button
											onclick={() => uiStore.toggleBacklinksPanel()}
											class="flex h-8 w-8 items-center justify-center rounded-md border {uiStore.backlinksPanelOpen
												? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
												: 'border-zinc-300 dark:border-zinc-600'}"
											title="Toggle backlinks panel (Cmd+Shift+B)"
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
											</svg>
										</button>
										<button
											onclick={() => uiStore.toggleLocalGraphPanel()}
											class="flex h-8 w-8 items-center justify-center rounded-md border {uiStore.localGraphPanelOpen
												? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
												: 'border-zinc-300 dark:border-zinc-600'}"
											title="Toggle local graph (Cmd+Shift+G)"
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
											</svg>
										</button>
										<button
											onclick={() => uiStore.toggleVersionHistoryPanel()}
											class="flex h-8 w-8 items-center justify-center rounded-md border {uiStore.versionHistoryPanelOpen
												? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
												: 'border-zinc-300 dark:border-zinc-600'}"
											title="Toggle version history (Cmd+Shift+H)"
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
										</button>
									</div>
								</div>
							{/snippet}
						</AIPanel>

						<!-- Editor or rendered view -->
						<div class="flex h-full flex-1 overflow-hidden">
							{#if uiStore.outlinePanelOpen && !editing}
								<aside class="w-56 shrink-0 overflow-y-auto border-r border-zinc-200 dark:border-zinc-800">
									<OutlinePanel body={entryStore.current?.body ?? ''} />
								</aside>
							{/if}
							<div class="flex-1 overflow-y-auto p-6">
								{#if editing && uiStore.editorMode === 'wysiwyg'}
									<div class="h-[calc(100vh-12rem)]">
										<TiptapEditor content={editorContent} onchange={onEditorChange} onsave={save} />
									</div>
								{:else if editing}
									<div class="h-[calc(100vh-12rem)]">
										<Editor content={editorContent} onchange={onEditorChange} onsave={save} />
									</div>
								{:else}
									<div class="prose dark:prose-invert max-w-4xl">
										{@html renderMarkdownWithLinks(entryStore.current?.body ?? '', resolvedIds)}
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
				{#if uiStore.localGraphPanelOpen}
					<LocalGraphPanel
						entryId={entryStore.current?.id ?? ''}
						kbName={entryStore.current?.kb_name ?? ''}
					/>
				{:else if uiStore.versionHistoryPanelOpen}
					<VersionHistoryPanel
						entryId={entryStore.current?.id ?? ''}
						kbName={entryStore.current?.kb_name ?? ''}
					/>
				{:else}
					<BacklinksPanel
						backlinks={entryStore.current?.backlinks ?? []}
						loading={entryStore.loading}
					/>
				{/if}
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

	function renderMarkdownWithLinks(md: string, existingIds: Set<string>): string {
		let html = marked.parse(md, { async: false, renderer }) as string;
		html = renderCallouts(html);
		html = renderWikilinks(html, existingIds.size > 0 ? existingIds : undefined);
		return html;
	}
</script>
