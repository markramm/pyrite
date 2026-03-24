// SSR is enabled globally (adapter-node).
// App routes load data client-side via onMount.
// Site routes use +page.server.ts for SSR data loading.
export const prerender = false;
