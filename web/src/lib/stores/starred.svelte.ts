/**
 * Starred entries store using Svelte 5 runes.
 */

import type { StarredEntryItem } from '$lib/api/types';
import { api } from '$lib/api/client';

let starred = $state<StarredEntryItem[]>([]);
let loading = $state(false);
let error = $state<string | null>(null);

/** Set of "entry_id:kb_name" for quick lookup */
let starredSet = $derived(new Set(starred.map((s) => `${s.entry_id}:${s.kb_name}`)));

export function useStarred() {
	async function load(kb?: string) {
		loading = true;
		error = null;
		try {
			const result = await api.getStarredEntries(kb);
			starred = result.starred;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load starred entries';
		} finally {
			loading = false;
		}
	}

	async function star(entryId: string, kbName: string) {
		try {
			await api.starEntry(entryId, kbName);
			await load();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to star entry';
		}
	}

	async function unstar(entryId: string, kb?: string) {
		try {
			await api.unstarEntry(entryId, kb);
			await load();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to unstar entry';
		}
	}

	function isStarred(entryId: string, kbName: string): boolean {
		return starredSet.has(`${entryId}:${kbName}`);
	}

	async function reorder(entries: { entry_id: string; kb_name: string; sort_order: number }[]) {
		try {
			await api.reorderStarred(entries);
			await load();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to reorder starred entries';
		}
	}

	return {
		get starred() {
			return starred;
		},
		get loading() {
			return loading;
		},
		get error() {
			return error;
		},
		load,
		star,
		unstar,
		isStarred,
		reorder
	};
}
