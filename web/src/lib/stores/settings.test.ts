import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	api: {
		getSettings: vi.fn(),
		setSetting: vi.fn()
	}
}));

import { api } from '$lib/api/client';
import { settingsStore } from './settings.svelte';

const mockGetSettings = vi.mocked(api.getSettings);
const mockSetSetting = vi.mocked(api.setSetting);

beforeEach(() => {
	vi.clearAllMocks();
	settingsStore.settings = {};
	settingsStore.loading = false;
	settingsStore.error = null;
});

describe('SettingsStore', () => {
	describe('load', () => {
		it('populates settings from API', async () => {
			mockGetSettings.mockResolvedValueOnce({
				settings: { theme: 'dark', language: 'en' }
			});

			await settingsStore.load();
			expect(settingsStore.settings).toEqual({ theme: 'dark', language: 'en' });
		});

		it('sets loading during request', async () => {
			mockGetSettings.mockImplementation(async () => {
				expect(settingsStore.loading).toBe(true);
				return { settings: {} };
			});

			await settingsStore.load();
			expect(settingsStore.loading).toBe(false);
		});

		it('sets error message on failure', async () => {
			mockGetSettings.mockRejectedValueOnce(new Error('Server error'));

			await settingsStore.load();
			expect(settingsStore.error).toBe('Server error');
			expect(settingsStore.loading).toBe(false);
		});
	});

	describe('set', () => {
		it('updates local settings immediately', async () => {
			mockSetSetting.mockResolvedValueOnce({ key: 'theme', value: 'light' });

			await settingsStore.set('theme', 'light');
			expect(settingsStore.settings['theme']).toBe('light');
		});

		it('calls api.setSetting', async () => {
			mockSetSetting.mockResolvedValueOnce({ key: 'theme', value: 'light' });

			await settingsStore.set('theme', 'light');
			expect(mockSetSetting).toHaveBeenCalledWith('theme', 'light');
		});

		it('sets error message on failure', async () => {
			mockSetSetting.mockRejectedValueOnce(new Error('Save failed'));

			await settingsStore.set('theme', 'light');
			expect(settingsStore.error).toBe('Save failed');
		});

		it('rolls back to the previous value when the save is refused', async () => {
			settingsStore.settings = { 'ai.model': 'old-model' };
			mockSetSetting.mockRejectedValueOnce(new Error('Insufficient permissions'));

			await settingsStore.set('ai.model', 'new-model');
			expect(settingsStore.settings['ai.model']).toBe('old-model');
		});

		it('removes a key that did not exist before a refused save', async () => {
			mockSetSetting.mockRejectedValueOnce(new Error('Insufficient permissions'));

			await settingsStore.set('ai.baseUrl', 'https://elsewhere.example');
			expect('ai.baseUrl' in settingsStore.settings).toBe(false);
		});

		it('keeps the value the server returns, so a secret is not held in the page', async () => {
			mockSetSetting.mockResolvedValueOnce({ key: 'ai.apiKey', value: '********' });

			await settingsStore.set('ai.apiKey', 'sk-typed-by-admin');
			expect(settingsStore.settings['ai.apiKey']).toBe('********');
		});
	});

	describe('get', () => {
		it('returns setting value', () => {
			settingsStore.settings = { theme: 'dark' };
			expect(settingsStore.get('theme')).toBe('dark');
		});

		it('returns defaultValue when key is missing', () => {
			expect(settingsStore.get('missing', 'fallback')).toBe('fallback');
			expect(settingsStore.get('missing')).toBe('');
		});
	});
});
