/** Routes with no `<svelte:head><title>` of their own (#49).
 *
 * `+layout.svelte` renders `<svelte:head><title>{brandStore.name}</title></svelte:head>`
 * only when `$page.route.id` is in this list. Svelte compiles a `<title>`
 * tag to a plain `document.title = …` assignment inside an effect — the
 * last such effect to run wins, there is no shared element a nested title
 * can "win against" by mounting later — so the only way the layout can
 * avoid ever clobbering a route's own title is to render *no* title effect
 * at all on a route that has one. Keeping the guard a static list (checked
 * against the routes on disk by untitled-routes.test.ts) means that
 * property holds regardless of effect ordering, navigation type, or
 * whether a route's title happens to re-render.
 *
 * Verify with: grep -rL "<title" web/src/routes/**\/+page.svelte
 */
export const UNTITLED_ROUTES = ['/tasks', '/settings/kbs', '/settings/kbs/[name]'];
