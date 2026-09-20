/** Brand title writer: gives the browser tab title a default without ever
 * clobbering a route's own `<svelte:head><title>` (#49).
 *
 * The root layout used to assign `document.title = brandStore.name`
 * unconditionally inside a `$effect`. Every route also declares its own
 * `<svelte:head><title>` (e.g. "Search — Pyrite"), which sets
 * `document.title` when the page mounts. The layout's effect fired
 * whenever branding finished loading and stomped whatever the page had
 * set, regardless of which happened first — a race, since it depends on
 * when `/config/branding` returns relative to the page mounting. See
 * kb/backlog/root-layout-overwrites-every-page-title-with-the-brand-name-49.md.
 *
 * The fix:
 *
 * - `applyBrandTitle` only overwrites `document.title` when nothing else
 *   has claimed it: either `document.title` is still the pristine static
 *   default (app.html's `<title>Pyrite</title>`, captured once) or it's
 *   exactly what this writer itself last wrote. Anything else means a
 *   route's own `<svelte:head><title>` got there first, and it wins.
 *   Covers the loading race in both orders on a single route.
 *
 * - Client-side navigation is the one case that comparison alone can't
 *   handle: navigating from a titled route to an untitled one leaves
 *   `document.title` holding the *outgoing* route's title, which looks
 *   exactly like "already claimed" even though the new route never
 *   claimed anything. `beginNavigation` (called from `onNavigate`, which
 *   fires before the new route's DOM replaces the old one — but never on
 *   the very first page load, where there is no "outgoing" title to be
 *   confused with) snapshots that pre-navigation value. `applyBrandTitle`
 *   (from `afterNavigate`, which fires once the new route's DOM —
 *   including any `<svelte:head><title>` it mounted — has settled) then
 *   knows: if `document.title` still equals that snapshot, nothing in
 *   the new route touched it, so the brand-name default applies; if it
 *   changed, the new route's own title already won.
 */

export interface BrandTitleState {
	/** document.title's value the instant this state was created — the
	 *  static fallback baked into app.html before any client JS ran. */
	staticDefault: string;
	/** The value this writer itself last assigned to document.title, or
	 *  null if it has not written since the last navigation began. */
	lastWritten: string | null;
	/** document.title as of the most recent beginNavigation() call, or
	 *  null when no navigation is in flight (initial load, or after
	 *  applyBrandTitle has already resolved this navigation). */
	pendingSnapshot: string | null;
}

export function createBrandTitleState(staticDefault: string): BrandTitleState {
	return { staticDefault, lastWritten: null, pendingSnapshot: null };
}

/** Call from onNavigate, before the new route's DOM replaces the current
 *  one, so applyBrandTitle can tell the outgoing route's leftover title
 *  apart from a claim made by the incoming route. */
export function beginNavigation(state: BrandTitleState): void {
	if (typeof document === 'undefined') return;
	state.pendingSnapshot = document.title;
}

/** Apply the brand name as document.title's default. No-ops when a route
 *  has already claimed the title. */
export function applyBrandTitle(state: BrandTitleState, brandName: string): void {
	if (typeof document === 'undefined') return;
	const current = document.title;

	if (state.pendingSnapshot !== null) {
		// A navigation is in flight (or just settled): unclaimed only if
		// nothing changed document.title since beginNavigation ran, i.e.
		// the new route didn't set its own <svelte:head><title>.
		const unclaimed = current === state.pendingSnapshot;
		state.pendingSnapshot = null;
		if (!unclaimed) return;
	} else {
		const unclaimed =
			state.lastWritten === null ? current === state.staticDefault : current === state.lastWritten;
		if (!unclaimed) return;
	}

	document.title = brandName;
	state.lastWritten = brandName;
}
