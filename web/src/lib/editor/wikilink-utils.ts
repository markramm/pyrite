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
 */
export function renderWikilinks(html: string): string {
	return html.replace(WIKILINK_REGEX, (_match, target: string, display?: string) => {
		const label = display?.trim() || target.trim();
		const href = `/entries/${encodeURIComponent(target.trim())}`;
		return `<a href="${href}" class="wikilink" data-wikilink="${target.trim()}">${label}</a>`;
	});
}
