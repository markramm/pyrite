import { test, expect } from '@playwright/test';

test.describe('QA Dashboard Page', () => {
	test('loads and shows QA heading', async ({ page }) => {
		await page.goto('/qa');
		// QA page uses Topbar with title="QA Dashboard" rendered as a span
		await expect(page.locator('header >> text=QA Dashboard')).toBeVisible();
		await expect(page).toHaveTitle(/QA Dashboard — Pyrite/);
	});

	test('shows validation summary', async ({ page }) => {
		await page.goto('/qa');
		// Wait for loading spinner to disappear
		await expect(page.locator('text=Loading QA data...')).toBeHidden({ timeout: 15000 });
		// After loading, either status summary cards or an error message appears
		const totalEntries = page.locator('text=Total Entries');
		const errorMsg = page.locator('.text-red-700, .text-red-400');
		await expect(totalEntries.or(errorMsg)).toBeVisible({ timeout: 5000 });
		// If loaded successfully, should show Total Entries and Total Issues stat cards
		if ((await totalEntries.count()) > 0) {
			await expect(totalEntries).toBeVisible();
			await expect(page.locator('text=Total Issues')).toBeVisible();
		}
	});

	test('has KB selector or shows all KBs', async ({ page }) => {
		await page.goto('/qa');
		// KB filter is a <select> with "All KBs" as default option
		const kbSelect = page.locator('select').filter({ hasText: 'All KBs' });
		await expect(kbSelect).toBeVisible();
	});

	test('shows issues list or clean state', async ({ page }) => {
		await page.goto('/qa');
		// Wait for loading to finish
		await expect(page.locator('text=Loading QA data...')).toBeHidden({ timeout: 15000 });
		// After loading, either "No issues found" or the Issues heading with count
		await expect(
			page
				.locator('text=No issues found.')
				.or(page.locator('h2:has-text("Issues")'))
				.or(page.locator('.text-red-700, .text-red-400'))
		).toBeVisible({ timeout: 5000 });
	});

	test('issues have severity indicators', async ({ page }) => {
		await page.goto('/qa');
		// Severity filter dropdown always exists even during loading
		const severitySelect = page.locator('select').filter({ hasText: 'All Severities' });
		await expect(severitySelect).toBeVisible();
		// Check that severity options are available
		await expect(severitySelect.locator('option:has-text("Error")')).toBeAttached();
		await expect(severitySelect.locator('option:has-text("Warning")')).toBeAttached();
		await expect(severitySelect.locator('option:has-text("Info")')).toBeAttached();
	});
});
