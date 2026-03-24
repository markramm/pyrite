// Disable SSR — this is a static SPA served from FastAPI.
// /site pages are pre-rendered to HTML by the site cache service.
export const ssr = false;
export const prerender = false;
