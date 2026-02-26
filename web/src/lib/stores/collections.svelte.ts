/** Collections store: collection list, active collection, entries */

import { api } from '$lib/api/client';
import type { CollectionResponse, EntryResponse } from '$lib/api/types';

class CollectionStore {
	collections = $state<CollectionResponse[]>([]);
	activeCollection = $state<CollectionResponse | null>(null);
	entries = $state<EntryResponse[]>([]);
	total = $state(0);
	loading = $state(false);
	error = $state<string | null>(null);
	viewMode = $state<'list' | 'table'>('list');

	async loadCollections(kb?: string) {
		this.loading = true;
		this.error = null;
		try {
			const res = await api.listCollections(kb);
			this.collections = res.collections;
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to load collections';
		} finally {
			this.loading = false;
		}
	}

	async loadCollection(id: string, kb: string) {
		this.loading = true;
		this.error = null;
		try {
			this.activeCollection = await api.getCollection(id, kb);
			const defaultView = (this.activeCollection.view_config?.default_view as string) ?? 'list';
			if (defaultView === 'table' || defaultView === 'list') {
				this.viewMode = defaultView;
			}
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to load collection';
			this.activeCollection = null;
		} finally {
			this.loading = false;
		}
	}

	async loadEntries(
		id: string,
		kb: string,
		options: { sort_by?: string; sort_order?: string; limit?: number; offset?: number } = {}
	) {
		this.loading = true;
		this.error = null;
		try {
			const res = await api.getCollectionEntries(id, kb, options);
			this.entries = res.entries;
			this.total = res.total;
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to load collection entries';
		} finally {
			this.loading = false;
		}
	}

	setViewMode(mode: 'list' | 'table') {
		this.viewMode = mode;
	}
}

export const collectionStore = new CollectionStore();
