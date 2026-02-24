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

	async set(key: string, value: string) {
		this.settings[key] = value;
		try {
			await api.setSetting(key, value);
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Failed to save setting';
		}
	}

	get(key: string, defaultValue = ''): string {
		return this.settings[key] ?? defaultValue;
	}
}

export const settingsStore = new SettingsStore();
