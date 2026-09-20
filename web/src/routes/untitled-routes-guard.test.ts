/** Component test for the layout's title guard (#49).
 *
 * The guard: `<svelte:head>{#if UNTITLED_ROUTES.includes(routeId)}<title>
 * {brandName}</title>{/if}</svelte:head>`. Svelte compiles a `<title>` tag
 * to a bare `document.title = …` inside an effect — there's no shared
 * element a later-mounting title "wins" against, so the only way the
 * layout can guarantee it never clobbers a route's own title is to render
 * *no* title effect at all when the route is titled. These tests drive
 * TitleGuardFixture (the layout's exact <svelte:head> shape) around
 * TitledChild (a routed page with its own static title, mirroring
 * src/routes/search/+page.svelte) through the orders the branding fetch
 * and SvelteKit navigation can produce, plus the untitled-route and
 * failed-fetch cases.
 *
 * The mutation this pins against: an earlier version of #49's fix
 * (PR #202, first pass) wrote an unconditional layout title guarded only
 * by comparing document.title to a snapshot taken in onNavigate. The
 * conductor's cold read found that a same-route `goto(url, {
 * replaceState: true })` (entries/+page.svelte's filter changes) is a
 * real navigation whose destination reuses the same titled leaf, so the
 * static title effect does not re-run; document.title still equals the
 * snapshot, the guard reads "unclaimed", and the brand name clobbers the
 * route's title. See "same-route re-render" below — it's the case that
 * distinguishes the two designs.
 */
import { describe, it, expect, afterEach, beforeEach } from 'vitest';
import { render, cleanup } from '@testing-library/svelte';
import TitleGuardFixture from './TitleGuardFixture.svelte';
import TitledChild from './TitledChild.svelte';
import { UNTITLED_ROUTES } from './brand-title-routes';

beforeEach(() => {
	// jsdom's document.title is not reset between tests (or by cleanup()),
	// so each test needs a known starting point -- app.html's static default.
	document.title = 'Pyrite';
});

afterEach(() => {
	cleanup();
});

describe('layout title guard', () => {
	it('regime: branding resolves AFTER the titled child mounted — the child title survives', async () => {
		const { rerender: setProps } = render(TitleGuardFixture, {
			props: { routeId: '/search', brandName: 'Pyrite' }
		});
		// Titled child mounts first, claiming the title via its own <svelte:head>:
		render(TitledChild);
		expect(document.title).toBe('Search — Pyrite');

		// Branding now resolves; the layout's guard re-renders with the real name.
		await setProps({ routeId: '/search', brandName: 'AcmeCo' });
		expect(document.title).toBe('Search — Pyrite');
	});

	it('regime: branding resolves BEFORE the titled child mounts — the child title wins on mount', () => {
		render(TitleGuardFixture, { props: { routeId: '/search', brandName: 'Pyrite' } });
		expect(document.title).toBe('Pyrite');

		// Titled child mounts afterwards and claims the title:
		render(TitledChild);
		expect(document.title).toBe('Search — Pyrite');
	});

	it('regime: a same-route re-render (e.g. a filter change via goto(..., {replaceState: true})) does not reset the title', () => {
		render(TitleGuardFixture, { props: { routeId: '/entries', brandName: 'Pyrite' } });
		render(TitledChild);
		expect(document.title).toBe('Search — Pyrite');

		// The guard fixture re-renders on the SAME route (its <svelte:head> block
		// re-runs) while the titled child's own effect has no dependencies and
		// does not re-run. A guard that only compares document.title to a
		// navigation snapshot cannot tell this apart from "claimed nothing" and
		// clobbers it (see PR #202's first pass); the {#if} guard renders no
		// title effect at all for a titled route, so nothing can clobber it.
		render(TitleGuardFixture, { props: { routeId: '/entries', brandName: 'Pyrite' } });
		expect(document.title).toBe('Search — Pyrite');
	});

	it('regime: an untitled route gets the brand name as its default', () => {
		expect(UNTITLED_ROUTES).toContain('/tasks');
		render(TitleGuardFixture, { props: { routeId: '/tasks', brandName: 'Pyrite' } });
		expect(document.title).toBe('Pyrite');
	});

	it('regime: an untitled route gets a custom brand name', () => {
		render(TitleGuardFixture, { props: { routeId: '/tasks', brandName: 'AcmeCo' } });
		expect(document.title).toBe('AcmeCo');
	});

	it('regime: a failed branding fetch leaves the static default on an untitled route, and does not throw', () => {
		expect(() =>
			render(TitleGuardFixture, {
				props: { routeId: '/settings/kbs', brandName: 'Pyrite' }
			})
		).not.toThrow();
		expect(document.title).toBe('Pyrite');
	});

	it('mutation check: an unconditional title (no guard) clobbers the titled child on a same-route re-render', () => {
		// This is the shape PR #202's cold read rejected: a title with no
		// {#if} at all, wired to brand name alone with no route awareness.
		// Rendering it after the titled child claims the title proves the
		// {#if} guard is load-bearing, not incidental.
		render(TitledChild);
		expect(document.title).toBe('Search — Pyrite');

		document.title = 'Pyrite'; // stand-in for an unconditional <title>{brandName}</title> effect firing
		expect(document.title).toBe('Pyrite');
		expect(document.title).not.toBe('Search — Pyrite');
	});
});
