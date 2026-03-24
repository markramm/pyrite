import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const baseUrl = url.origin;
	const kbsRes = await fetch('/api/kbs');
	const kbsData = await kbsRes.json();
	const kbs: Array<{ name: string }> = kbsData.kbs ?? [];

	const allEntries: Array<{ id: string; kb_name: string; updated_at?: string }> = [];
	for (const kb of kbs) {
		try {
			const res = await fetch(`/api/entries?kb=${encodeURIComponent(kb.name)}&limit=10000`);
			const data = await res.json();
			for (const entry of data.entries ?? []) {
				allEntries.push({ id: entry.id, kb_name: entry.kb_name ?? kb.name, updated_at: entry.updated_at });
			}
		} catch { /* skip */ }
	}

	const urls: string[] = [];
	urls.push(`  <url>\n    <loc>${baseUrl}/site</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>`);
	for (const kb of kbs) {
		urls.push(`  <url>\n    <loc>${baseUrl}/site/${encodeURIComponent(kb.name)}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>`);
	}
	for (const entry of allEntries) {
		const lastmod = entry.updated_at ? `\n    <lastmod>${entry.updated_at.split('T')[0]}</lastmod>` : '';
		urls.push(`  <url>\n    <loc>${baseUrl}/site/${encodeURIComponent(entry.kb_name)}/${encodeURIComponent(entry.id)}</loc>${lastmod}\n    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>`);
	}

	const sitemap = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join('\n')}\n</urlset>`;
	return new Response(sitemap, { headers: { 'Content-Type': 'application/xml', 'Cache-Control': 'max-age=3600' } });
};
