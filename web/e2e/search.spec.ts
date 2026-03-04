import { test, expect } from '@playwright/test';

test.describe('Search Page', () => {
	test('loads and shows search heading', async ({ page }) => {
		await page.goto('/search');
		// Search page uses Topbar breadcrumb with label "Search" inside the header
		await expect(page.locator('header nav >> text=Search')).toBeVisible();
		await expect(page).toHaveTitle(/Search — Pyrite/);
	});

	test('has search input field', async ({ page }) => {
		await page.goto('/search');
		const input = page.locator('input[type="text"][placeholder="Search entries..."]');
		await expect(input).toBeVisible();
	});

	test('has mode selector', async ({ page }) => {
		await page.goto('/search');
		// Mode buttons: keyword, semantic, hybrid
		await expect(page.locator('button:has-text("keyword")')).toBeVisible();
		await expect(page.locator('button:has-text("semantic")')).toBeVisible();
		await expect(page.locator('button:has-text("hybrid")')).toBeVisible();
	});

	test('search input accepts text', async ({ page }) => {
		await page.goto('/search');
		const input = page.locator('input[placeholder="Search entries..."]');
		await input.fill('test query');
		await expect(input).toHaveValue('test query');
	});

	test('submitting search shows results or empty state', async ({ page }) => {
		await page.goto('/search');
		const input = page.locator('input[placeholder="Search entries..."]');
		await input.fill('test');
		// Trigger the search by pressing Enter or waiting for input event
		await input.press('Enter');
		// Either results appear or "No results found" message
		await expect(
			page
				.locator('text=No results found')
				.or(page.locator('a[href^="/entries/"]').first())
		).toBeVisible({ timeout: 10000 });
	});

	test('search results have entry links', async ({ page }) => {
		await page.goto('/search');
		const input = page.locator('input[placeholder="Search entries..."]');
		await input.fill('test');
		await input.press('Enter');
		// Wait for results or empty state
		await expect(
			page
				.locator('text=No results found')
				.or(page.locator('a[href^="/entries/"]').first())
		).toBeVisible({ timeout: 10000 });
		// If results exist, they should be links to entries
		const results = page.locator('a[href^="/entries/"]');
		const count = await results.count();
		if (count > 0) {
			await expect(results.first()).toHaveAttribute('href', /\/entries\//);
		}
	});

	test('KB filter is available', async ({ page }) => {
		await page.goto('/search');
		// KB filter is a <select> with "All KBs" as default option
		const kbSelect = page.locator('select').filter({ hasText: 'All KBs' });
		await expect(kbSelect).toBeVisible();
	});

	test('mode selector changes search mode', async ({ page }) => {
		await page.goto('/search');
		// Default mode should be keyword (it has the active styling)
		const keywordBtn = page.locator('button:has-text("keyword")');
		const semanticBtn = page.locator('button:has-text("semantic")');
		const hybridBtn = page.locator('button:has-text("hybrid")');

		// Click semantic mode
		await semanticBtn.click();
		// The semantic button should now have the active gold styling
		await expect(semanticBtn).toHaveClass(/bg-gold/);

		// Click hybrid mode
		await hybridBtn.click();
		await expect(hybridBtn).toHaveClass(/bg-gold/);

		// Click keyword mode back
		await keywordBtn.click();
		await expect(keywordBtn).toHaveClass(/bg-gold/);
	});
});
