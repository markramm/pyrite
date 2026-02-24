import { test, expect } from '@playwright/test';

test.describe('Entry Detail Page', () => {
	test('shows outline and backlinks toggle buttons', async ({ page }) => {
		await page.goto('/entries');
		// Wait for entries to load, then click the first one
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		await expect(page.getByRole('button', { name: 'Outline' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Backlinks' })).toBeVisible();
	});

	test('outline button toggles outline panel', async ({ page }) => {
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		const outlineBtn = page.getByRole('button', { name: 'Outline' });
		await expect(outlineBtn).toBeVisible();

		// Click to open outline
		await outlineBtn.click();
		// Button should show active state (blue border)
		await expect(outlineBtn).toHaveClass(/border-blue-500/);

		// Click again to close
		await outlineBtn.click();
		await expect(outlineBtn).not.toHaveClass(/border-blue-500/);
	});
});
