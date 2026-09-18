import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
	test('loads and shows settings heading', async ({ page }) => {
		await page.goto('/settings');
		await expect(page.getByRole('heading', { name: 'Settings', level: 1 })).toBeVisible();
	});

	// #49 (github.com/markramm/pyrite/issues/49): web/src/routes/+layout.svelte
	// sets `document.title = brandStore.name` in an unconditional `$effect`
	// once branding finishes loading, clobbering this route's own
	// <svelte:head><title>Settings — Pyrite</title>. Reproduced live before
	// this rewrite: `toHaveTitle` receives "Pyrite", never "Settings —
	// Pyrite", on every run. +layout.svelte is outside this package's
	// footprint (not +page.svelte, not settings/**, not a lib component) so
	// it is not fixed here — see the theme's report for the conductor to
	// file/track.
	test.fixme(
		'sets the document title',
		async ({ page }) => {
			await page.goto('/settings');
			await expect(page).toHaveTitle(/Settings — Pyrite/);
		}
	);

	test('shows the General section with a Default KB input', async ({ page }) => {
		await page.goto('/settings');
		await expect(page.getByRole('heading', { name: 'General' })).toBeVisible();
		await expect(page.getByTestId('settings-default-kb-input')).toBeVisible();
	});

	test('shows the Appearance section with a Theme selector defaulting to Dark', async ({
		page
	}) => {
		await page.goto('/settings');
		await expect(page.getByRole('heading', { name: 'Appearance' })).toBeVisible();
		const themeSelect = page.getByTestId('settings-theme-select');
		await expect(themeSelect).toBeVisible();
		// The e2e world starts in dark mode (see app.spec.ts "Theme Toggle"),
		// and the settings page reads the current theme into this select's
		// value — dark, not merely present.
		await expect(themeSelect).toHaveValue('dark');
	});

	test('shows the AI Provider section', async ({ page }) => {
		await page.goto('/settings');
		await expect(page.getByRole('heading', { name: 'AI Provider' })).toBeVisible();
	});

	test('shows the Editor section', async ({ page }) => {
		await page.goto('/settings');
		await expect(page.getByRole('heading', { name: 'Editor' })).toBeVisible();
	});

	test('More section links to the KB, users, index, and plugins settings pages', async ({
		page
	}) => {
		await page.goto('/settings');
		await expect(page.getByRole('link', { name: 'My API Keys' })).toHaveAttribute(
			'href',
			'/settings/api-keys'
		);
		await expect(page.getByRole('link', { name: 'Knowledge Bases' })).toHaveAttribute(
			'href',
			'/settings/kbs'
		);
		await expect(page.getByRole('link', { name: 'Users & Permissions' })).toHaveAttribute(
			'href',
			'/settings/users'
		);
		await expect(page.getByRole('link', { name: 'Index Management' })).toHaveAttribute(
			'href',
			'/settings/index'
		);
		await expect(page.getByRole('link', { name: 'Plugins' })).toHaveAttribute(
			'href',
			'/settings/plugins'
		);
	});
});
