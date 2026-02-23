/** Search state with debounce */

import { api } from '$lib/api/client';
import type { SearchResult } from '$lib/api/types';

class SearchStore {
	query = $state('');
	results = $state<SearchResult[]>([]);
	loading = $state(false);
	error = $state<string | null>(null);

	private debounceTimer: ReturnType<typeof setTimeout> | null = null;

	setQuery(q: string) {
		this.query = q;
		if (this.debounceTimer) clearTimeout(this.debounceTimer);
		if (!q.trim()) {
			this.results = [];
			return;
		}
		this.debounceTimer = setTimeout(() => this.execute(), 300);
	}

	async execute(options: { kb?: string; type?: string } = {}) {
		if (!this.query.trim()) return;
		this.loading = true;
		this.error = null;
		try {
			const res = await api.search(this.query, { kb: options.kb, type: options.type });
			this.results = res.results;
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Search failed';
		} finally {
			this.loading = false;
		}
	}

	clear() {
		this.query = '';
		this.results = [];
	}
}

export const searchStore = new SearchStore();
