import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const [orientRes, entriesRes] = await Promise.all([
		fetch(`/api/kbs/${encodeURIComponent(params.kb)}/orient`),
		fetch(`/api/entries?kb=${encodeURIComponent(params.kb)}&limit=100`)
	]);

	const orient = orientRes.ok ? await orientRes.json() : null;
	const entries = await entriesRes.json();

	return {
		kb: params.kb,
		orient,
		entries: entries.entries ?? [],
		total: entries.total ?? 0
	};
};
