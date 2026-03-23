/** Search state with debounce */

import { api } from '$lib/api/client';
import type { SearchResult } from '$lib/api/types';

class SearchStore {
	query = $state('');
	results = $state<SearchResult[]>([]);
	loading = $state(false);
	error = $state<string | null>(null);
	mode = $state<'keyword' | 'semantic' | 'hybrid'>('keyword');

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

	async execute(
		options: {
			kb?: string;
			type?: string;
			mode?: 'keyword' | 'semantic' | 'hybrid';
			date_from?: string;
			date_to?: string;
			tags?: string;
		} = {}
	) {
		if (!this.query.trim()) return;
		this.loading = true;
		this.error = null;
		try {
			const res = await api.search(this.query, {
				kb: options.kb,
				type: options.type,
				mode: options.mode ?? this.mode,
				date_from: options.date_from,
				date_to: options.date_to,
				tags: options.tags,
			});
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
