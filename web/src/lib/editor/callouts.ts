/**
 * Callout renderer for marked.js.
 *
 * Converts Obsidian-compatible callout syntax in blockquotes:
 *   > [!info] Title
 *   > Content here
 *
 * Into styled callout divs:
 *   <div class="callout callout-info">
 *     <div class="callout-title">Title</div>
 *     <div class="callout-content"><p>Content here</p></div>
 *   </div>
 */

const CALLOUT_TYPES = new Set([
	'info',
	'warning',
	'tip',
	'note',
	'danger',
	'quote',
	'example',
	'bug',
	'question',
	'success',
	'failure',
	'abstract'
]);

/**
 * Post-processes HTML from marked to convert blockquotes with [!type] into callout divs.
 *
 * marked renders `> [!info] Title\n> Body` as:
 *   <blockquote>\n<p>[!info] Title\nBody</p>\n</blockquote>
 *
 * The title and body within a single <p> are separated by \n.
 * Multiple paragraphs produce multiple <p> tags inside the blockquote.
 */
export function renderCallouts(html: string): string {
	return html.replace(
		/<blockquote>\s*<p>\[!(\w+)\]([\s\S]*?)<\/blockquote>/g,
		(_match, type: string, rest: string) => {
			const normalizedType = type.toLowerCase();
			if (!CALLOUT_TYPES.has(normalizedType)) {
				return _match;
			}

			// rest starts right after [!type] and ends just before </blockquote>
			// Strip trailing \n and whitespace
			let inner = rest.replace(/\s*$/, '');

			// First line of `rest` (up to \n or </p>) is the title.
			// Everything after is content.
			let title: string;
			let content: string;

			// Split on first \n (within the <p>) or first </p> (end of first paragraph)
			const splitMatch = inner.match(/^([^\n]*?)(?:\n([\s\S]*)|\s*<\/p>([\s\S]*))$/);

			if (splitMatch) {
				title = splitMatch[1].trim();
				// Content is either after \n (same <p>) or after </p> (next <p>s)
				const afterNewline = splitMatch[2] ?? '';
				const afterCloseP = splitMatch[3] ?? '';

				if (afterNewline) {
					// Content was in same <p> tag — wrap in <p> and append rest
					// The afterNewline still ends with </p> possibly followed by more <p>s
					content = `<p>${afterNewline}`;
				} else {
					content = afterCloseP.trim();
				}
			} else {
				// No split found — just a type tag with optional title, no content
				title = inner.replace(/<\/p>\s*$/, '').trim();
				content = '';
			}

			// Default title = capitalized type name
			if (!title) {
				title = normalizedType.charAt(0).toUpperCase() + normalizedType.slice(1);
			}

			// Clean up content
			content = content.replace(/^\s*\n?\s*/, '').replace(/\s*$/, '');

			const contentHtml = content
				? `<div class="callout-content">${content}</div>`
				: '';

			return `<div class="callout callout-${normalizedType}"><div class="callout-title">${title}</div>${contentHtml}</div>`;
		}
	);
}
