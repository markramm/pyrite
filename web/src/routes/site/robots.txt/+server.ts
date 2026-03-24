import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url }) => {
	const body = `User-agent: *
Allow: /site/
Disallow: /app/
Disallow: /api/

Sitemap: ${url.origin}/site/sitemap.xml
`;
	return new Response(body, { headers: { 'Content-Type': 'text/plain' } });
};
