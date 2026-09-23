/** Settings store: syncs with backend settings API */

import { api } from '$lib/api/client';

class SettingsStore {
	settings = $state<Record<string, string>>({});
	loading = $state(false);
	error = $state<string | null>(null);

	async load() {
		this.loading = true;
		this.error = null;
		try {
			const resp = await api.getSettings();
			this.settings = resp.settings;
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to load settings';
		} finally {
			this.loading = false;
		}
	}

	/**
	 * Optimistic save. A refused save (e.g. a non-admin changing an operator
	 * setting) rolls back, so the page never shows a value the server does not
	 * hold; a successful one keeps what the server returns, which for a secret
	 * is its mask rather than the typed value.
	 */
	async set(key: string, value: string) {
		const had = key in this.settings;
		const previous = this.settings[key];
		this.settings[key] = value;
		try {
			const resp = await api.setSetting(key, value);
			if (resp && typeof resp.value === 'string') {
				this.settings[key] = resp.value;
			}
		} catch (e) {
			if (had) {
				this.settings[key] = previous;
			} else {
				delete this.settings[key];
			}
			this.error = e instanceof Error ? e.message : 'Failed to save setting';
		}
	}

	get(key: string, defaultValue = ''): string {
		return this.settings[key] ?? defaultValue;
	}
}

export const settingsStore = new SettingsStore();
