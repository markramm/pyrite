import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	api: {
		search: vi.fn()
	}
}));

import { api } from '$lib/api/client';
import { searchStore } from './search.svelte';

const mockSearch = vi.mocked(api.search);

beforeEach(() => {
	vi.clearAllMocks();
	vi.useFakeTimers();
	searchStore.query = '';
	searchStore.results = [];
	searchStore.loading = false;
	searchStore.error = null;
});

describe('SearchStore', () => {
	describe('execute', () => {
		it('calls API and populates results', async () => {
			searchStore.query = 'test query';
			mockSearch.mockResolvedValueOnce({
				query: 'test query',
				count: 1,
				results: [{ id: 'r1', kb_name: 'kb', entry_type: 'note', title: 'Result', tags: [] }]
			});

			await searchStore.execute();
			expect(searchStore.results).toHaveLength(1);
			expect(searchStore.results[0].title).toBe('Result');
		});

		it('does nothing with empty query', async () => {
			searchStore.query = '';
			await searchStore.execute();
			expect(mockSearch).not.toHaveBeenCalled();
		});

		it('handles errors', async () => {
			searchStore.query = 'test';
			mockSearch.mockRejectedValueOnce(new Error('Search failed'));
			await searchStore.execute();
			expect(searchStore.error).toBe('Search failed');
		});
	});

	describe('clear', () => {
		it('resets query and results', () => {
			searchStore.query = 'something';
			searchStore.results = [{ id: 'r1', kb_name: 'kb', entry_type: 'note', title: 'X', tags: [] }];
			searchStore.clear();
			expect(searchStore.query).toBe('');
			expect(searchStore.results).toHaveLength(0);
		});
	});

	describe('setQuery', () => {
		it('clears results when query is empty', () => {
			searchStore.results = [{ id: 'r1', kb_name: 'kb', entry_type: 'note', title: 'X', tags: [] }];
			searchStore.setQuery('');
			expect(searchStore.results).toHaveLength(0);
		});

		it('debounces API calls', async () => {
			mockSearch.mockResolvedValue({ query: 'hello', count: 0, results: [] });

			searchStore.setQuery('h');
			searchStore.setQuery('he');
			searchStore.setQuery('hello');

			// Should not have called yet
			expect(mockSearch).not.toHaveBeenCalled();

			// Advance past debounce delay
			await vi.advanceTimersByTimeAsync(350);

			// Should have called once with final query
			expect(mockSearch).toHaveBeenCalledTimes(1);
			expect(mockSearch).toHaveBeenCalledWith('hello', expect.any(Object));
		});
	});
});
