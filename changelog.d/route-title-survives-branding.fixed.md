- **A route's own page title was always overwritten with the brand name.**
  The root layout assigned `document.title = brandStore.name` unconditionally
  in a `$effect`, clobbering whatever `<svelte:head><title>` a route had set,
  regardless of which finished first — a race against when
  `/config/branding` returns. The layout now renders `<svelte:head><title>
  {brandStore.name}</title>` only for the handful of routes that declare no
  title of their own (`UNTITLED_ROUTES` in `web/src/routes/brand-title-routes.ts`,
  pinned against the routes on disk by a structural test); every other route
  never has a layout title effect to be clobbered by. (#49)
