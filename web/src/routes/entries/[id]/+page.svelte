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
	import { entryStore } from '$lib/stores/entries.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { aiChatStore } from '$lib/stores/ai.svelte';
	import { api } from '$lib/api/client';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import type { AITagSuggestion, AILinkSuggestion } from '$lib/api/types';

	let editing = $state(false);
	let editorContent = $state('');
	let aiMenuOpen = $state(false);
	let aiLoading = $state(false);

	// AI results
	let summaryResult = $state<string | null>(null);
	let tagSuggestions = $state<AITagSuggestion[]>([]);
	let linkSuggestions = $state<AILinkSuggestion[]>([]);
	let aiResultType = $state<'summary' | 'tags' | 'links' | null>(null);

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

		function handleClickOutside(e: MouseEvent) {
			if (aiMenuOpen) {
				const target = e.target as HTMLElement;
				if (!target.closest('.ai-menu-container')) {
					aiMenuOpen = false;
				}
			}
		}
		document.addEventListener('click', handleClickOutside);

		return () => {
			window.removeEventListener('keydown', handleKeydown);
			document.removeEventListener('click', handleClickOutside);
		};
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

	async function aiSummarize() {
		if (!entryStore.current) return;
		aiMenuOpen = false;
		aiLoading = true;
		aiResultType = 'summary';
		summaryResult = null;
		try {
			const res = await api.aiSummarize(entryStore.current.id, entryStore.current.kb_name);
			summaryResult = res.summary;
		} catch (e) {
			uiStore.toast(e instanceof Error ? e.message : 'Summarize failed', 'error');
			aiResultType = null;
		} finally {
			aiLoading = false;
		}
	}

	async function aiAutoTag() {
		if (!entryStore.current) return;
		aiMenuOpen = false;
		aiLoading = true;
		aiResultType = 'tags';
		tagSuggestions = [];
		try {
			const res = await api.aiAutoTag(entryStore.current.id, entryStore.current.kb_name);
			tagSuggestions = res.suggested_tags;
		} catch (e) {
			uiStore.toast(e instanceof Error ? e.message : 'Auto-tag failed', 'error');
			aiResultType = null;
		} finally {
			aiLoading = false;
		}
	}

	async function aiSuggestLinks() {
		if (!entryStore.current) return;
		aiMenuOpen = false;
		aiLoading = true;
		aiResultType = 'links';
		linkSuggestions = [];
		try {
			const res = await api.aiSuggestLinks(entryStore.current.id, entryStore.current.kb_name);
			linkSuggestions = res.suggestions;
		} catch (e) {
			uiStore.toast(e instanceof Error ? e.message : 'Suggest links failed', 'error');
			aiResultType = null;
		} finally {
			aiLoading = false;
		}
	}

	async function acceptTag(tag: AITagSuggestion) {
		if (!entryStore.current) return;
		const currentTags = entryStore.current.tags ?? [];
		if (currentTags.includes(tag.name)) return;
		try {
			await entryStore.save(entryStore.current.id, entryStore.current.kb_name, {
				tags: [...currentTags, tag.name]
			});
			tagSuggestions = tagSuggestions.filter((t) => t.name !== tag.name);
			uiStore.toast(`Tag "${tag.name}" added`, 'success');
		} catch {
			uiStore.toast('Failed to add tag', 'error');
		}
	}

	function dismissAIResult() {
		aiResultType = null;
		summaryResult = null;
		tagSuggestions = [];
		linkSuggestions = [];
	}

	function askAboutEntry() {
		if (!entryStore.current) return;
		aiChatStore.clear();
		uiStore.chatPanelOpen = true;
		aiChatStore.entryContext = {
			id: entryStore.current.id,
			kb: entryStore.current.kb_name,
			title: entryStore.current.title
		};
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

								<!-- AI menu -->
								<div class="ai-menu-container relative">
									<button
										onclick={() => (aiMenuOpen = !aiMenuOpen)}
										class="rounded-md border px-3 py-1 text-sm {aiMenuOpen
											? 'border-purple-500 bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
											: 'border-zinc-300 dark:border-zinc-600'}"
									>
										AI
									</button>
									{#if aiMenuOpen}
										<div class="absolute right-0 top-full z-50 mt-1 w-48 rounded-md border border-zinc-200 bg-white py-1 shadow-lg dark:border-zinc-700 dark:bg-zinc-800">
											<button
												onclick={aiSummarize}
												class="w-full px-3 py-2 text-left text-sm hover:bg-zinc-100 dark:hover:bg-zinc-700"
											>
												Summarize
											</button>
											<button
												onclick={aiAutoTag}
												class="w-full px-3 py-2 text-left text-sm hover:bg-zinc-100 dark:hover:bg-zinc-700"
											>
												Suggest Tags
											</button>
											<button
												onclick={aiSuggestLinks}
												class="w-full px-3 py-2 text-left text-sm hover:bg-zinc-100 dark:hover:bg-zinc-700"
											>
												Find Links
											</button>
											<hr class="my-1 border-zinc-200 dark:border-zinc-700" />
											<button
												onclick={askAboutEntry}
												class="w-full px-3 py-2 text-left text-sm hover:bg-zinc-100 dark:hover:bg-zinc-700"
											>
												Ask AI about this
											</button>
										</div>
									{/if}
								</div>

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
								<button
									onclick={() => uiStore.toggleLocalGraphPanel()}
									class="rounded-md border px-3 py-1 text-sm {uiStore.localGraphPanelOpen
										? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
										: 'border-zinc-300 dark:border-zinc-600'}"
									title="Toggle local graph (Cmd+Shift+G)"
								>
									Graph
								</button>
								<button
									onclick={() => uiStore.toggleVersionHistoryPanel()}
									class="rounded-md border px-3 py-1 text-sm {uiStore.versionHistoryPanelOpen
										? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
										: 'border-zinc-300 dark:border-zinc-600'}"
									title="Toggle version history (Cmd+Shift+H)"
								>
									History
								</button>
							</div>
						</div>

						<!-- AI Results banner -->
						{#if aiResultType}
							<div class="border-b border-zinc-200 bg-purple-50 px-6 py-3 dark:border-zinc-800 dark:bg-purple-900/20">
								<div class="flex items-start justify-between">
									<div class="flex-1">
										{#if aiLoading}
											<p class="text-sm text-purple-700 dark:text-purple-300">Processing...</p>
										{:else if aiResultType === 'summary' && summaryResult}
											<p class="mb-1 text-xs font-semibold uppercase text-purple-600 dark:text-purple-400">AI Summary</p>
											<p class="text-sm text-zinc-800 dark:text-zinc-200">{summaryResult}</p>
										{:else if aiResultType === 'tags' && tagSuggestions.length > 0}
											<p class="mb-2 text-xs font-semibold uppercase text-purple-600 dark:text-purple-400">Suggested Tags</p>
											<div class="flex flex-wrap gap-2">
												{#each tagSuggestions as tag}
													<button
														onclick={() => acceptTag(tag)}
														class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium {tag.is_new
															? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
															: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'} hover:opacity-80"
														title="{tag.reason}{tag.is_new ? ' (new tag)' : ''}"
													>
														{tag.name}
														<span class="text-[10px] opacity-60">+</span>
													</button>
												{/each}
											</div>
										{:else if aiResultType === 'tags'}
											<p class="text-sm text-zinc-500">No tag suggestions.</p>
										{:else if aiResultType === 'links' && linkSuggestions.length > 0}
											<p class="mb-2 text-xs font-semibold uppercase text-purple-600 dark:text-purple-400">Link Suggestions</p>
											<div class="space-y-1">
												{#each linkSuggestions as link}
													<div class="flex items-center gap-2 text-sm">
														<a
															href="/entries/{link.target_id}"
															class="font-medium text-blue-600 hover:underline dark:text-blue-400"
														>
															{link.target_title || link.target_id}
														</a>
														<span class="text-xs text-zinc-500">{link.reason}</span>
													</div>
												{/each}
											</div>
										{:else if aiResultType === 'links'}
											<p class="text-sm text-zinc-500">No link suggestions.</p>
										{/if}
									</div>
									{#if !aiLoading}
										<button
											onclick={dismissAIResult}
											class="ml-2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
										>
											&times;
										</button>
									{/if}
								</div>
							</div>
						{/if}

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
</script>
