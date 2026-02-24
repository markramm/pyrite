/**
 * Wikilink parsing and rendering utilities.
 *
 * Supports [[id]] and [[id|display text]] syntax.
 */

/** Regex matching wikilinks: [[target]] or [[target|display]] */
export const WIKILINK_REGEX = /\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g;

/** Single wikilink match result */
export interface WikilinkMatch {
	/** Full match including brackets: [[target|display]] */
	full: string;
	/** Target entry ID or title */
	target: string;
	/** Optional display text (undefined if not present) */
	display?: string;
	/** Start index in source string */
	start: number;
	/** End index in source string */
	end: number;
}

/**
 * Extract all wikilinks from a string.
 */
export function parseWikilinks(text: string): WikilinkMatch[] {
	const matches: WikilinkMatch[] = [];
	const regex = new RegExp(WIKILINK_REGEX.source, 'g');
	let match: RegExpExecArray | null;
	while ((match = regex.exec(text)) !== null) {
		matches.push({
			full: match[0],
			target: match[1].trim(),
			display: match[2]?.trim(),
			start: match.index,
			end: match.index + match[0].length
		});
	}
	return matches;
}

/**
 * Replace wikilinks in HTML with clickable links.
 * Used in the rendered markdown view.
 *
 * @param html - HTML string with [[wikilink]] syntax
 * @param existingIds - Optional set of entry IDs that exist. If provided,
 *   links to non-existent entries get a "wikilink-missing" class (red links).
 */
export function renderWikilinks(html: string, existingIds?: Set<string>): string {
	return html.replace(WIKILINK_REGEX, (_match, target: string, display?: string) => {
		const trimmed = target.trim();
		const label = display?.trim() || trimmed;
		const href = `/entries/${encodeURIComponent(trimmed)}`;
		const missing = existingIds && !existingIds.has(trimmed);
		const cls = missing ? 'wikilink wikilink-missing' : 'wikilink';
		return `<a href="${href}" class="${cls}" data-wikilink="${trimmed}">${label}</a>`;
	});
}
