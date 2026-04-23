/** Branding configuration returned by GET /config/branding. */
export interface BrandingConfig {
	name: string;
	tagline: string;
	primary_color: string;
	site_url: string;
	support_url: string;
	footer_credit_url: string;
	logo_url: string | null;
	wordmark_url: string | null;
	favicon_url: string | null;
	og_image_url: string | null;
	invert_on_dark: boolean;
	meta: { description: string };
}
