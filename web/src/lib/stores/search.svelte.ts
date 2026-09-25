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
	private requestId = 0;

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
		const requestId = ++this.requestId;
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
			if (requestId === this.requestId) this.results = res.results;
		} catch (e) {
			if (requestId === this.requestId) {
				this.error = e instanceof Error ? e.message : 'Search failed';
			}
		} finally {
			if (requestId === this.requestId) this.loading = false;
		}
	}

	clear() {
		this.query = '';
		this.results = [];
	}
}

export const searchStore = new SearchStore();
