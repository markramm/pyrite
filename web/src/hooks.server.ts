import type { Handle } from '@sveltejs/kit';

const API_BACKEND = process.env.PYRITE_API_URL || 'http://localhost:8088';

/**
 * Server hook: proxy /api and /auth requests to the Python backend.
 * Only applies during SSR — client-side fetch goes directly via the browser.
 */
export const handle: Handle = async ({ event, resolve }) => {
	const path = event.url.pathname;

	// Proxy API and auth requests to Python backend
	if (path.startsWith('/api/') || path.startsWith('/auth/')) {
		const targetUrl = `${API_BACKEND}${path}${event.url.search}`;
		const response = await fetch(targetUrl, {
			method: event.request.method,
			headers: event.request.headers,
			body: event.request.method !== 'GET' && event.request.method !== 'HEAD'
				? await event.request.text()
				: undefined,
		});

		return new Response(response.body, {
			status: response.status,
			statusText: response.statusText,
			headers: response.headers,
		});
	}

	return resolve(event);
};
