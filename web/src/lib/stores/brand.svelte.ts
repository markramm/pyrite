/** Brand store: loads white-label branding config from the server.
 *
 * The server's /config/branding endpoint is public (no auth required)
 * so this store can be loaded before the user logs in — the login
 * screen itself is branded.
 *
 * If the API call fails, we silently fall back to Pyrite defaults.
 * Branding is a display-only concern; a failed fetch should never
 * break the app.
 */

import { api } from '$lib/api/client';
import type { BrandingConfig } from '$lib/types/branding';

export const DEFAULT_BRAND: BrandingConfig & { loaded: boolean } = {
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
	meta: { description: '' },
	loaded: false
};

class BrandStore {
	name = $state<string>(DEFAULT_BRAND.name);
	tagline = $state<string>(DEFAULT_BRAND.tagline);
	primary_color = $state<string>(DEFAULT_BRAND.primary_color);
	site_url = $state<string>(DEFAULT_BRAND.site_url);
	support_url = $state<string>(DEFAULT_BRAND.support_url);
	footer_credit_url = $state<string>(DEFAULT_BRAND.footer_credit_url);
	logo_url = $state<string | null>(DEFAULT_BRAND.logo_url);
	wordmark_url = $state<string | null>(DEFAULT_BRAND.wordmark_url);
	favicon_url = $state<string | null>(DEFAULT_BRAND.favicon_url);
	og_image_url = $state<string | null>(DEFAULT_BRAND.og_image_url);
	invert_on_dark = $state<boolean>(DEFAULT_BRAND.invert_on_dark);
	meta = $state<{ description: string }>({ ...DEFAULT_BRAND.meta });
	loaded = $state<boolean>(false);

	async init() {
		try {
			const cfg = await api.getBrandingConfig();
			this.name = cfg.name;
			this.tagline = cfg.tagline;
			this.primary_color = cfg.primary_color;
			this.site_url = cfg.site_url;
			this.support_url = cfg.support_url;
			this.footer_credit_url = cfg.footer_credit_url;
			this.logo_url = cfg.logo_url;
			this.wordmark_url = cfg.wordmark_url;
			this.favicon_url = cfg.favicon_url;
			this.og_image_url = cfg.og_image_url;
			this.invert_on_dark = cfg.invert_on_dark;
			this.meta = cfg.meta ?? { description: '' };
		} catch {
			// Silent fallback — branding is display-only, never critical.
		}
		this.loaded = true;
	}
}

export const brandStore = new BrandStore();
