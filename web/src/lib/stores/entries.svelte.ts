/** Entry store: current entry, entry list, dirty state */

import { api } from '$lib/api/client';
import type { EntryResponse } from '$lib/api/types';

class EntryStore {
	entries = $state<EntryResponse[]>([]);
	current = $state<EntryResponse | null>(null);
	total = $state(0);
	limit = $state(50);
	offset = $state(0);
	loading = $state(false);
	saving = $state(false);
	error = $state<string | null>(null);
	dirty = $state(false);
	recentIds = $state<string[]>([]);

	async loadList(options: { kb?: string; entry_type?: string; offset?: number } = {}) {
		this.loading = true;
		this.error = null;
		try {
			const res = await api.listEntries({
				kb: options.kb,
				entry_type: options.entry_type,
				limit: this.limit,
				offset: options.offset ?? this.offset
			});
			this.entries = res.entries;
			this.total = res.total;
			this.offset = res.offset;
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to load entries';
		} finally {
			this.loading = false;
		}
	}

	async loadEntry(id: string, kb?: string) {
		this.loading = true;
		this.error = null;
		try {
			this.current = await api.getEntry(id, { kb, with_links: true });
			this.dirty = false;
			this.addRecent(id);
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to load entry';
			this.current = null;
		} finally {
			this.loading = false;
		}
	}

	async save(id: string, kb: string, updates: { title?: string; body?: string; tags?: string[] }) {
		this.saving = true;
		this.error = null;
		try {
			await api.updateEntry(id, { kb, ...updates });
			this.dirty = false;
			// Reload to get server-side updates
			await this.loadEntry(id, kb);
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to save';
			throw e;
		} finally {
			this.saving = false;
		}
	}

	markDirty() {
		this.dirty = true;
	}

	private addRecent(id: string) {
		this.recentIds = [id, ...this.recentIds.filter((r) => r !== id)].slice(0, 10);
	}
}

export const entryStore = new EntryStore();
