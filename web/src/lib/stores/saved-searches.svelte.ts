/** Saved search queries persisted to localStorage */

const STORAGE_KEY = 'pyrite-saved-searches';

export interface SavedSearch {
	name: string;
	query: string;
	mode: 'keyword' | 'semantic' | 'hybrid';
	kb?: string;
	type?: string;
	dateFrom?: string;
	dateTo?: string;
	tags?: string;
}

class SavedSearchStore {
	items = $state<SavedSearch[]>([]);

	constructor() {
		this.load();
	}

	load() {
		if (typeof localStorage === 'undefined') {
			this.items = [];
			return;
		}
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			this.items = raw ? JSON.parse(raw) : [];
		} catch {
			this.items = [];
		}
	}

	save(search: Omit<SavedSearch, 'kb' | 'type' | 'dateFrom' | 'dateTo' | 'tags'> & Partial<SavedSearch>) {
		const entry: SavedSearch = {
			name: search.name,
			query: search.query,
			mode: search.mode,
			kb: search.kb ?? '',
			type: search.type ?? '',
			dateFrom: search.dateFrom ?? '',
			dateTo: search.dateTo ?? '',
			tags: search.tags ?? '',
		};
		// Replace existing with same name, or append
		const idx = this.items.findIndex((s) => s.name === entry.name);
		if (idx >= 0) {
			this.items = [...this.items.slice(0, idx), entry, ...this.items.slice(idx + 1)];
		} else {
			this.items = [...this.items, entry];
		}
		this.persist();
	}

	remove(name: string) {
		this.items = this.items.filter((s) => s.name !== name);
		this.persist();
	}

	private persist() {
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(this.items));
		}
	}
}

export const savedSearches = new SavedSearchStore();
