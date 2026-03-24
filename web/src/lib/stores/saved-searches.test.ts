import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock localStorage
const store: Record<string, string> = {};
vi.stubGlobal('localStorage', {
	getItem: (key: string) => store[key] ?? null,
	setItem: (key: string, value: string) => { store[key] = value; },
	removeItem: (key: string) => { delete store[key]; },
});

import { savedSearches, type SavedSearch } from './saved-searches.svelte';

beforeEach(() => {
	for (const key of Object.keys(store)) delete store[key];
	// Reset the store state
	savedSearches.load();
});

describe('SavedSearches', () => {
	it('starts empty', () => {
		expect(savedSearches.items).toEqual([]);
	});

	it('saves a search', () => {
		savedSearches.save({
			name: 'My Search',
			query: 'test query',
			mode: 'keyword',
			kb: 'my-kb',
		});
		expect(savedSearches.items).toHaveLength(1);
		expect(savedSearches.items[0].name).toBe('My Search');
		expect(savedSearches.items[0].query).toBe('test query');
	});

	it('persists to localStorage', () => {
		savedSearches.save({ name: 'Persisted', query: 'hello', mode: 'semantic' });
		const raw = store['pyrite-saved-searches'];
		expect(raw).toBeDefined();
		const parsed = JSON.parse(raw);
		expect(parsed).toHaveLength(1);
		expect(parsed[0].name).toBe('Persisted');
	});

	it('loads from localStorage', () => {
		store['pyrite-saved-searches'] = JSON.stringify([
			{ name: 'Loaded', query: 'from storage', mode: 'hybrid', kb: '', type: '', dateFrom: '', dateTo: '', tags: '' }
		]);
		savedSearches.load();
		expect(savedSearches.items).toHaveLength(1);
		expect(savedSearches.items[0].name).toBe('Loaded');
	});

	it('removes a search by name', () => {
		savedSearches.save({ name: 'Keep', query: 'a', mode: 'keyword' });
		savedSearches.save({ name: 'Remove', query: 'b', mode: 'keyword' });
		expect(savedSearches.items).toHaveLength(2);
		savedSearches.remove('Remove');
		expect(savedSearches.items).toHaveLength(1);
		expect(savedSearches.items[0].name).toBe('Keep');
	});

	it('prevents duplicate names', () => {
		savedSearches.save({ name: 'Dupe', query: 'first', mode: 'keyword' });
		savedSearches.save({ name: 'Dupe', query: 'second', mode: 'semantic' });
		expect(savedSearches.items).toHaveLength(1);
		expect(savedSearches.items[0].query).toBe('second');
	});
});
