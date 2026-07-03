/**
 * Comment anchoring by quote + context windows.
 *
 * We deliberately do NOT store character offsets or ProseMirror positions:
 * the prose is edited freely, so any positional anchor breaks. Instead each
 * comment stores the selected `quote` plus a small leading/trailing context
 * window. To re-locate a comment we substring-search the current body for the
 * quote, disambiguating with context. If the passage was rewritten and the
 * quote no longer appears, the comment is "orphaned" rather than mis-anchored.
 */

export interface ReviewComment {
	id: string;
	author: string;
	created_at: string;
	quote: string;
	context_before: string;
	context_after: string;
	note: string;
	status: 'open' | 'resolved';
}

const CONTEXT_CHARS = 40;

/**
 * Capture the current text selection within a container element as a comment
 * anchor (quote + surrounding context). Returns null when there is no usable
 * text selection inside the container.
 */
export function captureSelectionAnchor(
	container: HTMLElement
): { quote: string; context_before: string; context_after: string } | null {
	const sel = typeof window !== 'undefined' ? window.getSelection() : null;
	if (!sel || sel.isCollapsed || sel.rangeCount === 0) return null;

	const quote = sel.toString().trim();
	if (!quote) return null;

	// Pull the container's full text and locate the quote to derive context.
	// Using textContent keeps this independent of the markdown/HTML rendering.
	const fullText = container.textContent ?? '';
	const idx = fullText.indexOf(quote);
	if (idx === -1) {
		// Selection spans rendering boundaries we can't map; still usable as a
		// bare quote with no context.
		return { quote, context_before: '', context_after: '' };
	}

	const before = fullText.slice(Math.max(0, idx - CONTEXT_CHARS), idx);
	const after = fullText.slice(idx + quote.length, idx + quote.length + CONTEXT_CHARS);
	return { quote, context_before: before, context_after: after };
}

export type AnchorMatch = { index: number; length: number } | null;

/**
 * Resolve a comment's quote to a position in the current body text.
 * Returns null when the passage can no longer be found (orphaned comment).
 *
 * Disambiguation: if the quote occurs multiple times, prefer the occurrence
 * whose surrounding text best matches the stored context windows.
 */
export function resolveAnchor(body: string, comment: ReviewComment): AnchorMatch {
	const { quote, context_before, context_after } = comment;
	if (!quote) return null;

	const occurrences: number[] = [];
	let from = 0;
	for (;;) {
		const i = body.indexOf(quote, from);
		if (i === -1) break;
		occurrences.push(i);
		from = i + Math.max(1, quote.length);
	}
	if (occurrences.length === 0) return null;
	if (occurrences.length === 1) return { index: occurrences[0], length: quote.length };

	// Score each occurrence by how much of the stored context it reproduces.
	let best = occurrences[0];
	let bestScore = -1;
	for (const i of occurrences) {
		const before = body.slice(Math.max(0, i - context_before.length), i);
		const after = body.slice(i + quote.length, i + quote.length + context_after.length);
		const score =
			commonSuffixLen(before, context_before) + commonPrefixLen(after, context_after);
		if (score > bestScore) {
			bestScore = score;
			best = i;
		}
	}
	return { index: best, length: quote.length };
}

/** True when the comment's passage can no longer be located in the body. */
export function isOrphaned(body: string, comment: ReviewComment): boolean {
	return resolveAnchor(body, comment) === null;
}

function commonPrefixLen(a: string, b: string): number {
	const n = Math.min(a.length, b.length);
	let i = 0;
	while (i < n && a[i] === b[i]) i++;
	return i;
}

function commonSuffixLen(a: string, b: string): number {
	const n = Math.min(a.length, b.length);
	let i = 0;
	while (i < n && a[a.length - 1 - i] === b[b.length - 1 - i]) i++;
	return i;
}
