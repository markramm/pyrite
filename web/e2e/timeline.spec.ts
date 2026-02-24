import { test, expect } from '@playwright/test';

test.describe('Timeline Page', () => {
	test('loads and shows timeline heading', async ({ page }) => {
		await page.goto('/timeline');
		await expect(page.getByRole('heading', { name: 'Timeline' })).toBeVisible();
	});

	test('shows filter controls', async ({ page }) => {
		await page.goto('/timeline');
		await expect(page.locator('input[type="date"]').first()).toBeVisible();
		await expect(page.locator('input[type="number"]')).toBeVisible();
		await expect(page.getByRole('button', { name: 'Apply' })).toBeVisible();
	});

	test('shows event count', async ({ page }) => {
		await page.goto('/timeline');
		// Wait for loading to finish
		await page.waitForSelector('text=/\\d+ events/');
		const countText = await page.locator('text=/\\d+ events/').textContent();
		expect(countText).toMatch(/\d+ events/);
	});

	test('shows events or empty state', async ({ page }) => {
		await page.goto('/timeline');
		// Either shows timeline events or "No timeline events found"
		await expect(
			page.locator('text=No timeline events found').or(page.locator('.callout, a[href^="/entries/"]').first())
		).toBeVisible({ timeout: 5000 });
	});

	test('date filter inputs accept values', async ({ page }) => {
		await page.goto('/timeline');
		const fromInput = page.locator('#date-from');
		await fromInput.fill('2025-01-01');
		await expect(fromInput).toHaveValue('2025-01-01');

		const toInput = page.locator('#date-to');
		await toInput.fill('2025-12-31');
		await expect(toInput).toHaveValue('2025-12-31');
	});

	test('importance filter accepts numeric value', async ({ page }) => {
		await page.goto('/timeline');
		const impInput = page.locator('#min-imp');
		await impInput.fill('5');
		await expect(impInput).toHaveValue('5');
	});
});
