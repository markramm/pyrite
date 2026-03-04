import { test, expect } from '@playwright/test';

test.describe('Collections Page', () => {
	test('loads and shows collections heading', async ({ page }) => {
		await page.goto('/collections');
		await expect(page.getByRole('heading', { name: 'Collections' })).toBeVisible();
		await expect(page).toHaveTitle(/Collections — Pyrite/);
	});

	test('shows collections list or empty state', async ({ page }) => {
		await page.goto('/collections');
		// Either collections grid items or "No collections found" empty state
		await expect(
			page
				.locator('text=No collections found')
				.or(page.locator('a[href^="/collections/"]').first())
		).toBeVisible({ timeout: 10000 });
	});

	test('has create collection button', async ({ page }) => {
		await page.goto('/collections');
		// "New Virtual Collection" link/button in the header area
		await expect(page.locator('a:has-text("New Virtual Collection")')).toBeVisible();
	});

	test('create button opens creation dialog or page', async ({ page }) => {
		await page.goto('/collections');
		const newBtn = page.locator('a:has-text("New Virtual Collection")');
		await expect(newBtn).toBeVisible();
		await newBtn.click();
		// Should navigate to /collections/new
		await expect(page).toHaveURL(/\/collections\/new/);
	});

	test('collection list items are clickable', async ({ page }) => {
		await page.goto('/collections');
		// Wait for loading to finish
		await expect(
			page
				.locator('text=No collections found')
				.or(page.locator('a[href^="/collections/"]').first())
		).toBeVisible({ timeout: 10000 });
		// If collections exist, they should be clickable links
		const items = page.locator('a[href^="/collections/"]').filter({ hasNot: page.locator('text=New Virtual Collection') });
		const count = await items.count();
		if (count > 0) {
			await expect(items.first()).toHaveAttribute('href', /\/collections\//);
		}
	});
});
