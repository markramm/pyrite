/** Unit tests for the root layout's title-writing guard (#49).
 *
 * The layout used to run `document.title = brandStore.name` inside an
 * unconditional `$effect`, clobbering whatever `<svelte:head><title>` a
 * route had already set. This is the issue's probe table inverted: a
 * route with its own title keeps it once branding has loaded; a route
 * with no title gets the brand name.
 *
 * Regimes covered (from the Groom/Triage on
 * kb/backlog/root-layout-overwrites-every-page-title-with-the-brand-name-49.md):
 *  - branding loads AFTER the page sets its title (today's clobber)
 *  - branding loads BEFORE the page sets its title (the other half of the race)
 *  - client-side navigation: titled -> untitled -> titled again
 *  - a custom (non-"Pyrite") brand name
 *  - a failed branding fetch: loaded flips true, name stays the static default,
 *    and applying it must not throw and must not stomp a route's title
 *
 * These exercise the pure brand-title.ts module the layout's `onNavigate`
 * / `afterNavigate` / branding-loaded `$effect` call into — see
 * +layout.svelte for the wiring and brand-title.ts's module doc for why
 * beginNavigation/applyBrandTitle are split the way they are.
 */
import { describe, it, expect } from 'vitest';
import { applyBrandTitle, beginNavigation, createBrandTitleState } from './brand-title';

describe('brand title writer', () => {
	it('initial load, untitled route: applyBrandTitle supplies the brand name as the default', () => {
		document.title = 'Pyrite'; // app.html's static default
		const state = createBrandTitleState('Pyrite');
		applyBrandTitle(state, 'Pyrite');
		expect(document.title).toBe('Pyrite');
	});

	it('regime: branding loads AFTER the page already set its own title — page title survives', () => {
		document.title = 'Pyrite';
		const state = createBrandTitleState('Pyrite');
		// The route mounts on initial load and claims the title via its own <svelte:head>:
		document.title = 'Search — Pyrite';
		// Branding now finishes loading and the effect fires for the first time:
		applyBrandTitle(state, 'Pyrite');
		expect(document.title).toBe('Search — Pyrite');
	});

	it('regime: branding loads BEFORE the page sets its title — page title still wins once it mounts', () => {
		document.title = 'Pyrite';
		const state = createBrandTitleState('Pyrite');
		// Branding finishes first; effect claims the default title:
		applyBrandTitle(state, 'Pyrite');
		expect(document.title).toBe('Pyrite');
		// Page mounts afterwards and sets its own title via <svelte:head>:
		document.title = 'Settings — Pyrite';
		// If the effect fires again for any reason, it must not stomp the page's title:
		applyBrandTitle(state, 'Pyrite');
		expect(document.title).toBe('Settings — Pyrite');
	});

	it('regime: client-side navigation from a titled route to an untitled one and back', () => {
		document.title = 'Pyrite';
		const state = createBrandTitleState('Pyrite');

		// Initial load lands on a titled route:
		document.title = 'Search — Pyrite';
		applyBrandTitle(state, 'Pyrite');
		expect(document.title).toBe('Search — Pyrite');

		// Navigate to an untitled route: onNavigate snapshots the outgoing
		// title, the new route mounts with no <svelte:head><title> of its own
		// (document.title is left untouched, still the old snapshot), then
		// afterNavigate applies the default.
		beginNavigation(state);
		// (new route's DOM settles here; it declares no title, so
		// document.title is unchanged from the snapshot)
		applyBrandTitle(state, 'Pyrite');
		expect(document.title).toBe('Pyrite');

		// Navigate to another titled route: onNavigate snapshots again, the
		// new route's own <svelte:head> changes document.title before
		// afterNavigate's applyBrandTitle call sees it.
		beginNavigation(state);
		document.title = 'Entries — Pyrite';
		applyBrandTitle(state, 'Pyrite');
		expect(document.title).toBe('Entries — Pyrite');
	});

	it('regime: a custom brand name is used as the fallback, not "Pyrite"', () => {
		document.title = 'Pyrite';
		const state = createBrandTitleState('Pyrite');
		applyBrandTitle(state, 'AcmeCo');
		expect(document.title).toBe('AcmeCo');
	});

	it('regime: a custom brand name does not override an already-titled route', () => {
		document.title = 'Pyrite';
		const state = createBrandTitleState('Pyrite');
		document.title = 'Search — Pyrite';
		applyBrandTitle(state, 'AcmeCo');
		expect(document.title).toBe('Search — Pyrite');
	});

	it('regime: a custom brand name survives navigation to an untitled route', () => {
		document.title = 'Pyrite';
		const state = createBrandTitleState('Pyrite');
		applyBrandTitle(state, 'AcmeCo');
		expect(document.title).toBe('AcmeCo');

		beginNavigation(state);
		// untitled route, document.title unchanged from the snapshot ('AcmeCo')
		applyBrandTitle(state, 'AcmeCo');
		expect(document.title).toBe('AcmeCo');
	});

	it('regime: a failed branding fetch leaves the static title and throws nothing', () => {
		document.title = 'Pyrite';
		const state = createBrandTitleState('Pyrite');
		// brandStore.init()'s catch swallows the error and leaves `name` at the
		// DEFAULT_BRAND value ("Pyrite"), then sets loaded=true regardless.
		// applyBrandTitle is called with that default name; it must not throw
		// and must leave the (already-correct) static title as-is.
		expect(() => applyBrandTitle(state, 'Pyrite')).not.toThrow();
		expect(document.title).toBe('Pyrite');
	});

	it('regime: a failed branding fetch does not stomp a route title already set', () => {
		document.title = 'Pyrite';
		const state = createBrandTitleState('Pyrite');
		document.title = 'Search — Pyrite';
		applyBrandTitle(state, 'Pyrite'); // brandStore.name still 'Pyrite' after a failed fetch
		expect(document.title).toBe('Search — Pyrite');
	});
});
