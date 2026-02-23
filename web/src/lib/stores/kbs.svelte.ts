/** KB list + active KB store using Svelte 5 runes */

import { api } from '$lib/api/client';
import type { KBInfo } from '$lib/api/types';

class KBStore {
	kbs = $state<KBInfo[]>([]);
	activeKB = $state<string | null>(null);
	loading = $state(false);
	error = $state<string | null>(null);

	get activeKBInfo(): KBInfo | undefined {
		return this.kbs.find((kb) => kb.name === this.activeKB);
	}

	async load() {
		this.loading = true;
		this.error = null;
		try {
			const res = await api.listKBs();
			this.kbs = res.kbs;
			// Default to first KB if none selected
			if (!this.activeKB && res.kbs.length > 0) {
				this.activeKB = res.kbs[0].name;
			}
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to load KBs';
		} finally {
			this.loading = false;
		}
	}

	setActive(name: string) {
		this.activeKB = name;
	}
}

export const kbStore = new KBStore();
