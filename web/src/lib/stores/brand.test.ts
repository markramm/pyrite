import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	api: {
		getBrandingConfig: vi.fn()
	}
}));

import { api } from '$lib/api/client';
import { brandStore, DEFAULT_BRAND } from './brand.svelte';

const mockGetBrandingConfig = vi.mocked(api.getBrandingConfig);

beforeEach(() => {
	vi.clearAllMocks();
	// Reset to defaults before each test
	Object.assign(brandStore, DEFAULT_BRAND);
	brandStore.loaded = false;
});

describe('brandStore', () => {
	describe('init', () => {
		it('loads branding from /config/branding and populates fields', async () => {
			mockGetBrandingConfig.mockResolvedValueOnce({
				name: 'Transparency Cascade Press',
				tagline: 'Tracing the money',
				primary_color: '#c93b3b',
				site_url: 'https://investigate.transparencycascade.org',
				support_url: 'mailto:contact@transparencycascade.org',
				footer_credit_url: 'https://pyrite.wiki',
				logo_url: '/branding/logo.png',
				wordmark_url: '/branding/wordmark.png',
				favicon_url: null,
				og_image_url: null,
				invert_on_dark: true,
				meta: { description: 'Investigative journalism.' }
			});

			await brandStore.init();

			expect(brandStore.name).toBe('Transparency Cascade Press');
			expect(brandStore.primary_color).toBe('#c93b3b');
			expect(brandStore.logo_url).toBe('/branding/logo.png');
			expect(brandStore.wordmark_url).toBe('/branding/wordmark.png');
			expect(brandStore.invert_on_dark).toBe(true);
			expect(brandStore.footer_credit_url).toBe('https://pyrite.wiki');
			expect(brandStore.loaded).toBe(true);
		});

		it('falls back to Pyrite defaults when the endpoint errors', async () => {
			mockGetBrandingConfig.mockRejectedValueOnce(new Error('network'));

			await brandStore.init();

			expect(brandStore.name).toBe('Pyrite');
			expect(brandStore.logo_url).toBeNull();
			expect(brandStore.loaded).toBe(true);
		});

		it('receives the footer credit URL from the API', async () => {
			mockGetBrandingConfig.mockResolvedValueOnce({
				name: 'Pyrite',
				tagline: '',
				primary_color: '#d4a017',
				site_url: '',
				support_url: '',
				footer_credit_url: 'https://pyrite.wiki',
				logo_url: null,
				wordmark_url: null,
				favicon_url: null,
				og_image_url: null,
				invert_on_dark: false,
				meta: { description: '' }
			});

			await brandStore.init();

			expect(brandStore.footer_credit_url).toBe('https://pyrite.wiki');
		});
	});
});
