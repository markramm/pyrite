import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch('/api/kbs');
	const data = await res.json();
	return { kbs: data.kbs ?? [] };
};
