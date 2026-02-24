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

	const entries = await refreshTitleCache();

	// Filter entries by query (case-insensitive prefix/substring)
	const lowerQuery = query.toLowerCase();
	const filtered = query
		? entries.filter(
				(e) =>
					e.title.toLowerCase().includes(lowerQuery) || e.id.toLowerCase().includes(lowerQuery)
			)
		: entries;

	const options: Completion[] = filtered.slice(0, 50).map((e) => ({
		label: e.title,
		detail: e.entry_type,
		apply: (view: EditorView, completion: Completion, from: number, to: number) => {
			// Replace from [[ to cursor with id]], keeping any existing display text
			const fullLine = view.state.doc.lineAt(from);
			const afterCursor = fullLine.text.slice(to - fullLine.from);
			const hasClosing = afterCursor.startsWith(']]');
			const insert = `${e.id}${hasClosing ? '' : ']]'}`;
			view.dispatch({ changes: { from, to, insert } });
		}
	}));

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
		readonly display: string
	) {
		super();
	}

	toDOM(): HTMLElement {
		const span = document.createElement('span');
		span.className =
			'wikilink-pill cursor-pointer rounded bg-blue-500/15 px-1.5 py-0.5 text-blue-600 hover:bg-blue-500/25 dark:text-blue-400';
		span.textContent = this.display;
		span.title = this.target;
		span.addEventListener('click', () => {
			window.location.href = `/entries/${encodeURIComponent(this.target)}`;
		});
		return span;
	}

	eq(other: WikilinkWidget): boolean {
		return this.target === other.target && this.display === other.display;
	}

	ignoreEvent(): boolean {
		return false;
	}
}

/** Regex for matching wikilinks in the document (supports [[kb:target|display]]). */
const wikilinkPattern = /\[\[(?:([a-z0-9-]+):)?([^\]|]+?)(?:\|([^\]]+?))?\]\]/g;

const wikilinkMatcher = new MatchDecorator({
	regexp: wikilinkPattern,
	decoration: (match, _view, pos) => {
		const kb = match[1]?.trim();
		const target = match[2].trim();
		const display = match[3]?.trim() || (kb ? `${kb}:${target}` : target);
		return Decoration.replace({
			widget: new WikilinkWidget(target, display)
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
	return [wikilinkDecorations];
}
