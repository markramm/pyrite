import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	api: {
		listEntries: vi.fn(),
		getEntry: vi.fn(),
		updateEntry: vi.fn()
	}
}));

import { api } from '$lib/api/client';
import { entryStore } from './entries.svelte';

const mockListEntries = vi.mocked(api.listEntries);
const mockGetEntry = vi.mocked(api.getEntry);
const mockUpdateEntry = vi.mocked(api.updateEntry);

const sampleEntry = {
	id: 'test-entry',
	kb_name: 'test-kb',
	entry_type: 'note',
	title: 'Test Note',
	body: '# Hello',
	tags: ['test'],
	participants: [],
	sources: [],
	outlinks: [],
	backlinks: [],
	file_path: '/tmp/test.md'
};

beforeEach(() => {
	vi.clearAllMocks();
	entryStore.entries = [];
	entryStore.current = null;
	entryStore.total = 0;
	entryStore.offset = 0;
	entryStore.loading = false;
	entryStore.saving = false;
	entryStore.error = null;
	entryStore.dirty = false;
});

describe('EntryStore', () => {
	describe('loadList', () => {
		it('populates entries from API', async () => {
			mockListEntries.mockResolvedValueOnce({
				entries: [sampleEntry],
				total: 1,
				limit: 50,
				offset: 0
			});

			await entryStore.loadList({ kb: 'test-kb' });
			expect(entryStore.entries).toHaveLength(1);
			expect(entryStore.total).toBe(1);
		});

		it('handles API errors gracefully', async () => {
			mockListEntries.mockRejectedValueOnce(new Error('Server error'));
			await entryStore.loadList();
			expect(entryStore.error).toBe('Server error');
		});
	});

	describe('loadEntry', () => {
		it('sets current entry and clears dirty flag', async () => {
			mockGetEntry.mockResolvedValueOnce(sampleEntry);

			entryStore.dirty = true;
			await entryStore.loadEntry('test-entry', 'test-kb');
			expect(entryStore.current?.id).toBe('test-entry');
			expect(entryStore.dirty).toBe(false);
		});

		it('adds to recent IDs', async () => {
			mockGetEntry.mockResolvedValueOnce(sampleEntry);
			await entryStore.loadEntry('test-entry');
			expect(entryStore.recentIds).toContain('test-entry');
		});

		it('deduplicates recent IDs', async () => {
			mockGetEntry.mockResolvedValue(sampleEntry);
			await entryStore.loadEntry('test-entry');
			await entryStore.loadEntry('test-entry');
			const count = entryStore.recentIds.filter((id) => id === 'test-entry').length;
			expect(count).toBe(1);
		});
	});

	describe('save', () => {
		it('calls updateEntry and reloads', async () => {
			mockUpdateEntry.mockResolvedValueOnce({ updated: true, id: 'test-entry' });
			mockGetEntry.mockResolvedValueOnce(sampleEntry);

			await entryStore.save('test-entry', 'test-kb', { body: 'Updated' });
			expect(mockUpdateEntry).toHaveBeenCalledWith('test-entry', { kb: 'test-kb', body: 'Updated' });
			expect(entryStore.dirty).toBe(false);
		});

		it('propagates errors and keeps dirty flag', async () => {
			mockUpdateEntry.mockRejectedValueOnce(new Error('Save failed'));

			await expect(entryStore.save('x', 'kb', { body: '...' })).rejects.toThrow('Save failed');
			expect(entryStore.error).toBe('Save failed');
		});
	});

	describe('markDirty', () => {
		it('sets dirty flag', () => {
			expect(entryStore.dirty).toBe(false);
			entryStore.markDirty();
			expect(entryStore.dirty).toBe(true);
		});
	});
});
