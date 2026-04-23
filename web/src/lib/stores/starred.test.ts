import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	api: {
		getStarredEntries: vi.fn(),
		starEntry: vi.fn(),
		unstarEntry: vi.fn(),
		reorderStarred: vi.fn()
	}
}));

import { api } from '$lib/api/client';
import { useStarred } from './starred.svelte';

const mockGetStarred = vi.mocked(api.getStarredEntries);
const mockStarEntry = vi.mocked(api.starEntry);
const mockUnstarEntry = vi.mocked(api.unstarEntry);
const mockReorderStarred = vi.mocked(api.reorderStarred);

const store = useStarred();

const sampleStarred = [
	{
		entry_id: 'entry-1',
		kb_name: 'kb-1',
		sort_order: 0,
		title: 'First',
		created_at: '2026-01-01T00:00:00Z'
	},
	{
		entry_id: 'entry-2',
		kb_name: 'kb-2',
		sort_order: 1,
		title: 'Second',
		created_at: '2026-01-02T00:00:00Z'
	}
];

beforeEach(async () => {
	vi.clearAllMocks();
	// Reset module-level state by loading empty
	mockGetStarred.mockResolvedValueOnce({ count: 0, starred: [] });
	await store.load();
	vi.clearAllMocks();
});

describe('useStarred', () => {
	describe('load', () => {
		it('populates starred from API', async () => {
			mockGetStarred.mockResolvedValueOnce({ count: 2, starred: sampleStarred });

			await store.load();

			expect(mockGetStarred).toHaveBeenCalledOnce();
			expect(store.starred).toHaveLength(2);
			expect(store.starred[0].entry_id).toBe('entry-1');
			expect(store.starred[1].entry_id).toBe('entry-2');
		});

		it('handles error and sets error message', async () => {
			mockGetStarred.mockRejectedValueOnce(new Error('Network error'));

			await store.load();

			expect(store.error).toBe('Network error');
		});

		it('sets loading during request', async () => {
			let capturedLoading: boolean | undefined;
			mockGetStarred.mockImplementationOnce(async () => {
				capturedLoading = store.loading;
				return { count: 0, starred: [] };
			});

			await store.load();

			expect(capturedLoading).toBe(true);
			expect(store.loading).toBe(false);
		});
	});

	describe('star', () => {
		it('calls api.starEntry then reloads', async () => {
			mockStarEntry.mockResolvedValueOnce({ starred: true, entry_id: 'entry-1', kb_name: 'kb-1' });
			mockGetStarred.mockResolvedValueOnce({ count: 2, starred: sampleStarred });

			await store.star('entry-1', 'kb-1');

			expect(mockStarEntry).toHaveBeenCalledWith('entry-1', 'kb-1');
			expect(mockGetStarred).toHaveBeenCalledOnce();
		});

		it('handles error', async () => {
			mockStarEntry.mockRejectedValueOnce(new Error('Star failed'));

			await store.star('entry-1', 'kb-1');

			expect(store.error).toBe('Star failed');
		});
	});

	describe('unstar', () => {
		it('calls api.unstarEntry then reloads', async () => {
			mockUnstarEntry.mockResolvedValueOnce({ unstarred: true, entry_id: 'entry-1' });
			mockGetStarred.mockResolvedValueOnce({ count: 0, starred: [] });

			await store.unstar('entry-1', 'kb-1');

			expect(mockUnstarEntry).toHaveBeenCalledWith('entry-1', 'kb-1');
			expect(mockGetStarred).toHaveBeenCalledOnce();
		});
	});

	describe('isStarred', () => {
		it('returns true for starred entry', async () => {
			mockGetStarred.mockResolvedValueOnce({ count: 2, starred: sampleStarred });
			await store.load();

			expect(store.isStarred('entry-1', 'kb-1')).toBe(true);
		});

		it('returns false for non-starred entry', async () => {
			mockGetStarred.mockResolvedValueOnce({ count: 2, starred: sampleStarred });
			await store.load();

			expect(store.isStarred('entry-99', 'kb-1')).toBe(false);
		});
	});

	describe('reorder', () => {
		it('calls api.reorderStarred then reloads', async () => {
			const reorderPayload = [
				{ entry_id: 'entry-2', kb_name: 'kb-2', sort_order: 0 },
				{ entry_id: 'entry-1', kb_name: 'kb-1', sort_order: 1 }
			];
			mockReorderStarred.mockResolvedValueOnce({ reordered: true, count: 2 });
			mockGetStarred.mockResolvedValueOnce({ count: 2, starred: sampleStarred });

			await store.reorder(reorderPayload);

			expect(mockReorderStarred).toHaveBeenCalledWith(reorderPayload);
			expect(mockGetStarred).toHaveBeenCalledOnce();
		});

		it('handles error', async () => {
			mockReorderStarred.mockRejectedValueOnce(new Error('Reorder failed'));

			await store.reorder([]);

			expect(store.error).toBe('Reorder failed');
		});
	});
});
