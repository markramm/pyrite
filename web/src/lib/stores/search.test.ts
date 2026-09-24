import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	api: {
		search: vi.fn()
	}
}));

import { api } from '$lib/api/client';
import { searchStore } from './search.svelte';

const mockSearch = vi.mocked(api.search);

function response(title: string) {
	const result = { id: title, kb_name: 'kb', entry_type: 'note', title, tags: [] };
	return { query: title, count: 1, results: [result] };
}

function deferred<T>() {
	let resolve!: (value: T) => void;
	let reject!: (reason: unknown) => void;
	const promise = new Promise<T>((res, rej) => {
		resolve = res;
		reject = rej;
	});
	return { promise, resolve, reject };
}

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

		it('ignores older responses and keeps loading until the latest settles', async () => {
			const first = deferred<ReturnType<typeof response>>();
			const second = deferred<ReturnType<typeof response>>();
			mockSearch.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
			searchStore.query = 'abc';
			const firstSearch = searchStore.execute();
			searchStore.query = 'abcdef';
			const secondSearch = searchStore.execute();
			first.resolve(response('abc'));
			await firstSearch;
			expect(searchStore.loading).toBe(true);
			expect(searchStore.results).toHaveLength(0);
			second.resolve(response('abcdef'));
			await secondSearch;
			expect(searchStore.loading).toBe(false);
			expect(searchStore.results[0].title).toBe('abcdef');
		});

		it('ignores an older error after the latest response succeeds', async () => {
			const first = deferred<ReturnType<typeof response>>();
			const second = deferred<ReturnType<typeof response>>();
			mockSearch.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
			searchStore.query = 'abc';
			const firstSearch = searchStore.execute();
			searchStore.query = 'abcdef';
			const secondSearch = searchStore.execute();
			second.resolve(response('abcdef'));
			await secondSearch;
			first.reject(new Error('Old search failed'));
			await firstSearch;
			expect(searchStore.error).toBeNull();
			expect(searchStore.results[0].title).toBe('abcdef');
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
