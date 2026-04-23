import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	api: {
		listCollections: vi.fn(),
		getCollection: vi.fn(),
		getCollectionEntries: vi.fn()
	}
}));

import { api } from '$lib/api/client';
import { collectionStore } from './collections.svelte';

const mockListCollections = vi.mocked(api.listCollections);
const mockGetCollection = vi.mocked(api.getCollection);
const mockGetCollectionEntries = vi.mocked(api.getCollectionEntries);

const sampleCollection = {
	id: 'col-1',
	kb_name: 'test-kb',
	title: 'Test Collection',
	description: 'A test collection',
	source_type: 'query',
	icon: '',
	entry_count: 0,
	folder_path: '',
	tags: [],
	query: '',
	view_config: { default_view: 'table' }
};

const sampleEntry = {
	id: 'entry-1',
	kb_name: 'test-kb',
	entry_type: 'note',
	title: 'Test Note',
	body: '# Hello',
	tags: [],
	participants: [],
	sources: [],
	outlinks: [],
	backlinks: [],
	file_path: '/tmp/test.md'
};

beforeEach(() => {
	vi.clearAllMocks();
	collectionStore.collections = [];
	collectionStore.activeCollection = null;
	collectionStore.entries = [];
	collectionStore.total = 0;
	collectionStore.loading = false;
	collectionStore.error = null;
	collectionStore.viewMode = 'list';
});

describe('CollectionStore', () => {
	describe('loadCollections', () => {
		it('populates collections array', async () => {
			mockListCollections.mockResolvedValueOnce({
				collections: [sampleCollection],
				total: 1
			});

			await collectionStore.loadCollections('test-kb');
			expect(collectionStore.collections).toHaveLength(1);
			expect(collectionStore.collections[0].id).toBe('col-1');
		});

		it('handles error', async () => {
			mockListCollections.mockRejectedValueOnce(new Error('Network error'));

			await collectionStore.loadCollections();
			expect(collectionStore.error).toBe('Network error');
			expect(collectionStore.loading).toBe(false);
		});
	});

	describe('loadCollection', () => {
		it('sets activeCollection', async () => {
			mockGetCollection.mockResolvedValueOnce(sampleCollection);

			await collectionStore.loadCollection('col-1', 'test-kb');
			expect(collectionStore.activeCollection).toEqual(sampleCollection);
		});

		it('sets viewMode from view_config.default_view', async () => {
			mockGetCollection.mockResolvedValueOnce(sampleCollection);

			await collectionStore.loadCollection('col-1', 'test-kb');
			expect(collectionStore.viewMode).toBe('table');
		});

		it('sets activeCollection to null on error', async () => {
			collectionStore.activeCollection = sampleCollection;
			mockGetCollection.mockRejectedValueOnce(new Error('Not found'));

			await collectionStore.loadCollection('col-1', 'test-kb');
			expect(collectionStore.activeCollection).toBeNull();
			expect(collectionStore.error).toBe('Not found');
		});

		it('defaults to list when no view_config', async () => {
			// Tests the store's defensive handling of null view_config from older
			// API responses. Cast through unknown because the typed shape requires
			// a record.
			const collectionNoConfig = { ...sampleCollection, view_config: null } as unknown as typeof sampleCollection;
			mockGetCollection.mockResolvedValueOnce(collectionNoConfig);

			collectionStore.viewMode = 'table';
			await collectionStore.loadCollection('col-1', 'test-kb');
			expect(collectionStore.viewMode).toBe('list');
		});
	});

	describe('loadEntries', () => {
		it('populates entries and total', async () => {
			mockGetCollectionEntries.mockResolvedValueOnce({
				entries: [sampleEntry],
				total: 1,
				collection_id: 'col-1'
			});

			await collectionStore.loadEntries('col-1', 'test-kb');
			expect(collectionStore.entries).toHaveLength(1);
			expect(collectionStore.total).toBe(1);
		});

		it('passes sort/limit/offset options', async () => {
			mockGetCollectionEntries.mockResolvedValueOnce({
				entries: [],
				total: 0,
				collection_id: 'col-1'
			});

			const options = { sort_by: 'title', sort_order: 'asc', limit: 10, offset: 20 };
			await collectionStore.loadEntries('col-1', 'test-kb', options);
			expect(mockGetCollectionEntries).toHaveBeenCalledWith('col-1', 'test-kb', options);
		});

		it('handles error', async () => {
			mockGetCollectionEntries.mockRejectedValueOnce(new Error('Server error'));

			await collectionStore.loadEntries('col-1', 'test-kb');
			expect(collectionStore.error).toBe('Server error');
			expect(collectionStore.loading).toBe(false);
		});
	});

	describe('setViewMode', () => {
		it('updates viewMode', () => {
			expect(collectionStore.viewMode).toBe('list');
			collectionStore.setViewMode('kanban');
			expect(collectionStore.viewMode).toBe('kanban');
		});
	});
});
