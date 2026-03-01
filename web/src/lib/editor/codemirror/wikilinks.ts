/**
 * CodeMirror 6 extension for wikilink support.
 *
 * Provides:
 * - Autocomplete triggered by [[ with entry title suggestions
 * - Decorations rendering wikilinks as styled pills when cursor is outside
 */

import type { Completion, CompletionContext, CompletionResult } from '@codemirror/autocomplete';
import type { Extension } from '@codemirror/state';
import {
	Decoration,
	type DecorationSet,
	EditorView,
	MatchDecorator,
	ViewPlugin,
	type ViewUpdate,
	WidgetType
} from '@codemirror/view';
import { api } from '$lib/api/client';
import type { EntryTitle } from '$lib/api/types';

// =============================================================================
// Autocomplete
// =============================================================================

/** Cache of entry titles for autocomplete, refreshed periodically. */
let titleCache: EntryTitle[] = [];
let cacheTimestamp = 0;
const CACHE_TTL = 30_000; // 30 seconds

async function refreshTitleCache(): Promise<EntryTitle[]> {
	const now = Date.now();
	if (titleCache.length > 0 && now - cacheTimestamp < CACHE_TTL) {
		return titleCache;
	}
	try {
		const res = await api.getEntryTitles({ limit: 2000 });
		titleCache = res.entries;
		cacheTimestamp = now;
	} catch {
		// Keep stale cache on error
	}
	return titleCache;
}

/**
 * Autocomplete source for wikilinks.
 * Triggers when user types `[[` and provides entry title suggestions.
 */
export async function wikilinkCompletions(
	context: CompletionContext
): Promise<CompletionResult | null> {
	// Look for [[ before cursor
	const line = context.state.doc.lineAt(context.pos);
	const textBefore = line.text.slice(0, context.pos - line.from);

	// Find the last [[ that isn't closed
	const openIdx = textBefore.lastIndexOf('[[');
	if (openIdx === -1) return null;

	// Make sure there's no ]] between [[ and cursor
	const afterOpen = textBefore.slice(openIdx + 2);
	if (afterOpen.includes(']]')) return null;

	// Extract what the user has typed after [[
	const query = afterOpen.split('|')[0]; // Don't include display text portion
	const from = line.from + openIdx + 2;

	// Check for fragment syntax (two-stage completion)
	const hashIdx = query.indexOf('#');
	const caretIdx = query.indexOf('^');

	if (hashIdx !== -1 || caretIdx !== -1) {
		// Second stage: complete heading or block ID
		const separatorIdx = hashIdx !== -1 ? hashIdx : caretIdx;
		const entryId = query.slice(0, separatorIdx).trim();
		const fragmentQuery = query.slice(separatorIdx + 1).toLowerCase();
		const fragmentType = hashIdx !== -1 ? 'heading' : 'block';

		if (!entryId) return null;

		// Find the KB for this entry
		const entries = await refreshTitleCache();
		const entry = entries.find((e) => e.id === entryId || e.title.toLowerCase() === entryId.toLowerCase());
		if (!entry) return null;

		try {
			const blockOptions: { heading?: string; block_type?: string; block_id?: string } = {};
			if (fragmentType === 'heading') {
				blockOptions.block_type = 'heading';
			}
			const res = await api.getEntryBlocks(entryId, entry.kb_name, blockOptions);
			const blocks = res.blocks || [];

			const lowerFragment = fragmentQuery.toLowerCase();
			const filtered = fragmentQuery
				? blocks.filter(
						(b: { block_id: string; heading?: string; content: string }) =>
							(b.block_id?.toLowerCase().includes(lowerFragment)) ||
							(b.heading?.toLowerCase().includes(lowerFragment)) ||
							(b.content?.toLowerCase().includes(lowerFragment))
					)
				: blocks;

			const options: Completion[] = filtered.slice(0, 30).map((b: { block_id: string; heading?: string; content: string }) => ({
				label: fragmentType === 'heading' ? (b.heading || b.block_id) : b.block_id,
				detail: b.content?.slice(0, 60),
				apply: (view: EditorView, _completion: Completion, applyFrom: number, applyTo: number) => {
					// Replace from separator+1 to cursor
					const fragmentFrom = line.from + openIdx + 2 + separatorIdx + 1;
					const fullLine = view.state.doc.lineAt(fragmentFrom);
					const afterCursor = fullLine.text.slice(applyTo - fullLine.from);
					const hasClosing = afterCursor.startsWith(']]');
					const insertValue = fragmentType === 'heading' ? (b.heading || b.block_id) : b.block_id;
					const insert = `${insertValue}${hasClosing ? '' : ']]'}`;
					view.dispatch({ changes: { from: fragmentFrom, to: applyTo, insert } });
				}
			}));

			return {
				from: line.from + openIdx + 2 + separatorIdx + 1,
				to: context.pos,
				options,
				filter: false
			};
		} catch {
			return null;
		}
	}

	const entries = await refreshTitleCache();

	// Filter entries by query (case-insensitive prefix/substring)
	const lowerQuery = query.toLowerCase();
	const filtered = query
		? entries.filter(
				(e) =>
					e.title.toLowerCase().includes(lowerQuery) ||
					e.id.toLowerCase().includes(lowerQuery) ||
					(e.aliases ?? []).some((a) => a.toLowerCase().includes(lowerQuery))
			)
		: entries;

	const options: Completion[] = filtered.slice(0, 50).map((e) => {
		const matchedAlias = (e.aliases ?? []).find((a) => a.toLowerCase().includes(lowerQuery));
		return {
			label: e.title,
			detail: matchedAlias ? `${e.entry_type} (alias: ${matchedAlias})` : e.entry_type,
			apply: (view: EditorView, completion: Completion, from: number, to: number) => {
				const fullLine = view.state.doc.lineAt(from);
				const afterCursor = fullLine.text.slice(to - fullLine.from);
				const hasClosing = afterCursor.startsWith(']]');
				const insert = `${e.id}${hasClosing ? '' : ']]'}`;
				view.dispatch({ changes: { from, to, insert } });
			}
		};
	});

	return {
		from,
		to: context.pos,
		options,
		filter: false // We already filtered
	};
}

// =============================================================================
// Wikilink Decorations (pills)
// =============================================================================

/** Widget that renders a wikilink as a styled pill. */
class WikilinkWidget extends WidgetType {
	constructor(
		readonly target: string,
		readonly display: string,
		readonly heading?: string,
		readonly blockId?: string
	) {
		super();
	}

	toDOM(): HTMLElement {
		const span = document.createElement('span');
		span.className =
			'wikilink-pill cursor-pointer rounded bg-blue-500/15 px-1.5 py-0.5 text-blue-600 hover:bg-blue-500/25 dark:text-blue-400';
		span.textContent = this.display;
		span.title = this.target + (this.heading ? `#${this.heading}` : '') + (this.blockId ? `^${this.blockId}` : '');
		span.addEventListener('click', () => {
			let fragment = '';
			if (this.heading) fragment = `#${encodeURIComponent(this.heading)}`;
			else if (this.blockId) fragment = `#block-${encodeURIComponent(this.blockId)}`;
			window.location.href = `/entries/${encodeURIComponent(this.target)}${fragment}`;
		});
		return span;
	}

	eq(other: WikilinkWidget): boolean {
		return this.target === other.target && this.display === other.display
			&& this.heading === other.heading && this.blockId === other.blockId;
	}

	ignoreEvent(): boolean {
		return false;
	}
}

/** Regex for matching wikilinks in the document (supports [[kb:target#heading^block|display]]). */
const wikilinkPattern = /\[\[(?:([a-z0-9-]+):)?([^\]|#^]+?)(?:#([^\]|^]+?))?(?:\^([^\]|]+?))?(?:\|([^\]]+?))?\]\]/g;

const wikilinkMatcher = new MatchDecorator({
	regexp: wikilinkPattern,
	decoration: (match, _view, pos) => {
		const kb = match[1]?.trim();
		const target = match[2].trim();
		const heading = match[3]?.trim();
		const blockId = match[4]?.trim();
		const displayText = match[5]?.trim();

		let display: string;
		if (displayText) {
			display = displayText;
		} else if (heading) {
			const base = kb ? `${kb}:${target}` : target;
			display = `${base} \u00A7 ${heading}`;
		} else if (blockId) {
			const base = kb ? `${kb}:${target}` : target;
			display = `${base} ^${blockId}`;
		} else {
			display = kb ? `${kb}:${target}` : target;
		}

		return Decoration.replace({
			widget: new WikilinkWidget(target, display, heading, blockId)
		});
	}
});

/** ViewPlugin that shows wikilink pills when the cursor is not inside the link. */
const wikilinkDecorations = ViewPlugin.fromClass(
	class {
		decorations: DecorationSet;

		constructor(view: EditorView) {
			this.decorations = wikilinkMatcher.createDeco(view);
		}

		update(update: ViewUpdate) {
			this.decorations = wikilinkMatcher.updateDeco(update, this.decorations);
		}
	},
	{
		decorations: (v) => {
			// Hide decorations when cursor is inside a wikilink
			const { from, to } = v.view.state.selection.main;
			const doc = v.view.state.doc;

			// Find if cursor is inside any wikilink
			const line = doc.lineAt(from);
			const lineText = line.text;
			const regex = new RegExp(wikilinkPattern.source, 'g');
			let match;
			while ((match = regex.exec(lineText)) !== null) {
				const start = line.from + match.index;
				const end = start + match[0].length;
				if (from >= start && to <= end) {
					// Cursor is inside this wikilink — filter it out
					return v.decorations.update({
						filter: (decoFrom, decoTo) => !(decoFrom === start && decoTo === end)
					});
				}
			}
			return v.decorations;
		}
	}
);

// =============================================================================
// Transclusion Decorations (embedded cards)
// =============================================================================

/** Widget that renders a transclusion as a read-only embedded card. */
class TransclusionWidget extends WidgetType {
	constructor(
		readonly target: string,
		readonly heading?: string,
		readonly blockId?: string
	) {
		super();
	}

	toDOM(): HTMLElement {
		const wrapper = document.createElement('div');
		wrapper.className = 'transclusion-card';
		wrapper.style.cssText =
			'border: 1px solid #374151; border-left: 3px solid #3b82f6; padding: 0.75rem; margin: 0.5rem 0; border-radius: 4px; background: rgba(59,130,246,0.05); cursor: default;';
		wrapper.contentEditable = 'false';

		// Header label
		const label = document.createElement('div');
		label.style.cssText = 'color: #9ca3af; font-size: 0.85em; margin-bottom: 0.5rem;';
		const fragment = this.heading ? ` \u00A7 ${this.heading}` : this.blockId ? ` ^${this.blockId}` : '';
		label.textContent = `\u{1F4CE} ${this.target}${fragment}`;
		wrapper.appendChild(label);

		// Content area (loading state)
		const content = document.createElement('div');
		content.className = 'transclusion-content';
		content.style.cssText = 'color: #d1d5db; font-size: 0.9em;';
		content.textContent = 'Loading...';
		wrapper.appendChild(content);

		// Source link
		const cite = document.createElement('div');
		cite.style.cssText = 'margin-top: 0.5rem; font-size: 0.8em;';
		const link = document.createElement('a');
		link.href = `/entries/${encodeURIComponent(this.target)}`;
		link.textContent = this.target;
		link.style.cssText = 'color: #3b82f6; text-decoration: underline;';
		link.addEventListener('click', (e) => {
			e.preventDefault();
			window.location.href = link.href;
		});
		cite.appendChild(link);
		wrapper.appendChild(cite);

		// Async load content
		this._loadContent(content);

		return wrapper;
	}

	private async _loadContent(contentEl: HTMLElement): Promise<void> {
		try {
			const res = await api.resolveEntry(this.target);
			if (res.resolved && res.entry) {
				let body: string;

				if (this.blockId) {
					// Fetch specific block by ID
					const blocksRes = await api.getEntryBlocks(res.entry.id, res.entry.kb_name, {
						block_id: this.blockId
					});
					const matchingBlock = blocksRes.blocks?.find(
						(b) => b.block_id === this.blockId
					);
					if (matchingBlock) {
						body = matchingBlock.content;
					} else {
						// Fallback to full body if block not found
						const entryRes = await api.getEntry(res.entry.id, { kb: res.entry.kb_name });
						body = entryRes.body || '';
					}
				} else {
					const entryRes = await api.getEntry(res.entry.id, { kb: res.entry.kb_name });
					body = entryRes.body || '';

					if (this.heading) {
						const headingRegex = new RegExp(
							`^##?#?#?#?#?\\s+${this.heading.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*$`,
							'mi'
						);
						const match = headingRegex.exec(body);
						if (match) {
							const start = match.index + match[0].length;
							const nextHeading = body.slice(start).search(/^##?#?#?#?#?\s+/m);
							body =
								nextHeading === -1
									? body.slice(start).trim()
									: body.slice(start, start + nextHeading).trim();
						}
					}
				}
				contentEl.textContent = body.slice(0, 500) + (body.length > 500 ? '...' : '');
			} else {
				contentEl.textContent = '\u26A0 Entry not found';
			}
		} catch {
			contentEl.textContent = '\u26A0 Failed to load';
		}
	}

	eq(other: TransclusionWidget): boolean {
		return (
			this.target === other.target &&
			this.heading === other.heading &&
			this.blockId === other.blockId
		);
	}

	ignoreEvent(): boolean {
		return true;
	}
}

/** Regex for matching transclusions in the document (supports ![[kb:target#heading^block|display]]). */
const transclusionPattern =
	/!\[\[(?:([a-z0-9-]+):)?([^\]|#^]+?)(?:#([^\]|^]+?))?(?:\^([^\]|]+?))?(?:\|([^\]]+?))?\]\]/g;

const transclusionMatcher = new MatchDecorator({
	regexp: transclusionPattern,
	decoration: (match) => {
		const target = match[2].trim();
		const heading = match[3]?.trim();
		const blockId = match[4]?.trim();

		return Decoration.replace({
			widget: new TransclusionWidget(target, heading, blockId)
		});
	}
});

/** ViewPlugin that shows transclusion cards. */
const transclusionDecorations = ViewPlugin.fromClass(
	class {
		decorations: DecorationSet;

		constructor(view: EditorView) {
			this.decorations = transclusionMatcher.createDeco(view);
		}

		update(update: ViewUpdate) {
			this.decorations = transclusionMatcher.updateDeco(update, this.decorations);
		}
	},
	{
		decorations: (v) => {
			// Hide decorations when cursor is inside a transclusion
			const { from, to } = v.view.state.selection.main;
			const doc = v.view.state.doc;

			const line = doc.lineAt(from);
			const lineText = line.text;
			const regex = new RegExp(transclusionPattern.source, 'g');
			let match;
			while ((match = regex.exec(lineText)) !== null) {
				const start = line.from + match.index;
				const end = start + match[0].length;
				if (from >= start && to <= end) {
					return v.decorations.update({
						filter: (decoFrom, decoTo) => !(decoFrom === start && decoTo === end)
					});
				}
			}
			return v.decorations;
		}
	}
);

// =============================================================================
// Export
// =============================================================================

/**
 * CodeMirror extension for wikilink support.
 * Includes autocomplete on [[ and styled pill decorations.
 *
 * Note: autocomplete is configured centrally in setup.ts, which combines
 * the wikilink completion source with slash commands and other sources.
 */
export function wikilinkExtension(): Extension {
	return [wikilinkDecorations, transclusionDecorations];
}
