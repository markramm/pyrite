import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const res = await fetch(
		`/api/entries/${encodeURIComponent(params.id)}?kb=${encodeURIComponent(params.kb)}&with_links=true`
	);
	if (!res.ok) {
		return { entry: null, kb: params.kb, id: params.id };
	}
	const entry = await res.json();
	return { entry, kb: params.kb, id: params.id };
};
