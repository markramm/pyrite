/** Shared constants for Pyrite frontend. */

/** Color mapping for entry types, used in search results and graph views. */
export const typeColors: Record<string, string> = {
	event: '#3b82f6',
	person: '#8b5cf6',
	organization: '#f59e0b',
	topic: '#10b981',
	note: '#6b7280',
	place: '#ef4444',
	source: '#06b6d4',
	document: '#84cc16',
	standard: '#f472b6',
	component: '#22d3ee',
	adr: '#a78bfa',
	backlog_item: '#fb923c',
};

/** Default color for unknown entry types. */
export const defaultTypeColor = '#71717a';

/** Get the color for an entry type, falling back to default. */
export function typeColor(entryType: string): string {
	return typeColors[entryType] ?? defaultTypeColor;
}
