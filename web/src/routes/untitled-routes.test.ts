/** Structural pin for the root layout's title guard (#49).
 *
 * `+layout.svelte` renders a brand-name `<title>` only for the routes in
 * UNTITLED_ROUTES — the ones that declare no `<svelte:head><title>` of
 * their own. If the layout rendered a title unconditionally instead, it
 * would clobber every other route's own title the moment its effect
 * re-ran after the page mounted (see the conductor review on #202: a
 * same-route `goto(..., { replaceState: true })` doesn't re-run a titled
 * page's static `<title>` effect, so a naive comparison-based guard can't
 * tell "re-claimed the same title" from "claimed nothing" — the layout
 * must simply never render a title effect on a titled route at all).
 *
 * This test reads every +page.svelte under src/routes (via Vite's
 * import.meta.glob, as raw source — no node:fs/node:path, which this
 * project deliberately doesn't type; see vite.config.ts's `declare const
 * process`) and asserts the set without a <svelte:head><title> equals
 * UNTITLED_ROUTES, so a new untitled page silently falls back to
 * "Pyrite" in every tab instead of the list quietly rotting.
 */
import { describe, it, expect } from 'vitest';
import { UNTITLED_ROUTES } from './brand-title-routes';

// Eagerly loaded raw source of every +page.svelte, keyed by a path relative
// to this file, e.g. "./tasks/+page.svelte", "./search/+page.svelte".
const pageFiles = import.meta.glob('./**/+page.svelte', { eager: true, query: '?raw', import: 'default' }) as Record<
	string,
	string
>;

/** Mirror SvelteKit's file-path -> route.id mapping for the subset of
 *  conventions this app's routes actually use (no route groups). */
function toRouteId(globKey: string): string {
	// globKey looks like "./tasks/+page.svelte" or "./+page.svelte".
	const dir = globKey.replace(/^\.\/?/, '').replace(/\/?\+page\.svelte$/, '');
	return dir === '' ? '/' : '/' + dir;
}

describe('UNTITLED_ROUTES', () => {
	it('is exactly the set of +page.svelte files with no <svelte:head><title>', () => {
		const actuallyUntitled = Object.entries(pageFiles)
			.filter(([, source]) => !source.includes('<title'))
			.map(([key]) => toRouteId(key))
			.sort();

		expect(actuallyUntitled).toEqual([...UNTITLED_ROUTES].sort());
	});
});
