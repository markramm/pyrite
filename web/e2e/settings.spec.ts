import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
	test('loads and shows settings heading', async ({ page }) => {
		await page.goto('/settings');
		await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
		await expect(page).toHaveTitle(/Settings — Pyrite/);
	});

	test('shows KB list', async ({ page }) => {
		await page.goto('/settings');
		// Settings page has a General section with "Default KB" input
		await expect(page.locator('text=Default KB')).toBeVisible();
	});

	test('has theme or config options', async ({ page }) => {
		await page.goto('/settings');
		// Appearance section with Theme selector
		await expect(page.getByRole('heading', { name: 'Appearance' })).toBeVisible();
		await expect(page.locator('text=Theme')).toBeVisible();
		// Theme dropdown with Light/Dark options
		const themeSelect = page.locator('select').filter({ hasText: 'Dark' });
		await expect(themeSelect).toBeVisible();
		// General section
		await expect(page.getByRole('heading', { name: 'General' })).toBeVisible();
		// AI Provider section
		await expect(page.getByRole('heading', { name: 'AI Provider' })).toBeVisible();
		// Editor section
		await expect(page.getByRole('heading', { name: 'Editor' })).toBeVisible();
	});
});
