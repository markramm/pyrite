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
		await expect(page.getByLabel('Toggle outline panel')).toBeAttached();
		await expect(page.getByLabel('Toggle backlinks panel')).toBeAttached();
	});

	test('outline button toggles outline panel', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		const outlineBtn = page.getByLabel('Toggle outline panel');
		await expect(outlineBtn).toBeVisible();

		// Click to open outline — button should show active state (blue border)
		await outlineBtn.click();
		await expect(outlineBtn).toHaveClass(/border-blue-500/);

		// Click again to close
		await outlineBtn.click();
		await expect(outlineBtn).not.toHaveClass(/border-blue-500/);
	});

	test('backlinks button toggles backlinks panel', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		const backlinksBtn = page.getByLabel('Toggle backlinks panel');
		await expect(backlinksBtn).toBeVisible();

		// Click to open backlinks panel
		await backlinksBtn.click();
		await expect(backlinksBtn).toHaveClass(/border-blue-500/);

		// Click again to close
		await backlinksBtn.click();
		await expect(backlinksBtn).not.toHaveClass(/border-blue-500/);
	});

	test('version history button toggles version history panel', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		const historyBtn = page.getByLabel('Toggle version history');
		await expect(historyBtn).toBeVisible();

		await historyBtn.click();
		await expect(historyBtn).toHaveClass(/border-blue-500/);

		await historyBtn.click();
		await expect(historyBtn).not.toHaveClass(/border-blue-500/);
	});

	test('local graph button toggles local graph panel', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		const graphBtn = page.getByLabel('Toggle local graph');
		await expect(graphBtn).toBeVisible();

		await graphBtn.click();
		await expect(graphBtn).toHaveClass(/border-blue-500/);

		await graphBtn.click();
		await expect(graphBtn).not.toHaveClass(/border-blue-500/);
	});

	test('entry metadata displays type and KB name', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		// Metadata sidebar shows Type and KB fields
		await expect(page.locator('text=Type:').first()).toBeVisible({ timeout: 5000 });
		await expect(page.locator('text=KB:').first()).toBeVisible();
	});

	test('entry metadata displays ID and file path', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		await expect(page.locator('text=ID:').first()).toBeVisible({ timeout: 5000 });
		await expect(page.locator('text=File:').first()).toBeVisible();
	});

	test('edit button switches to editor mode', async ({ page }) => {
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		const editBtn = page.locator('button', { hasText: 'Edit' });
		await expect(editBtn).toBeVisible({ timeout: 5000 });

		await editBtn.click();
		// After clicking Edit, "View" and "Save" buttons should appear
		await expect(page.locator('button', { hasText: 'View' })).toBeVisible();
		await expect(page.locator('button', { hasText: 'Save' })).toBeVisible();
	});

	test('edit mode shows editor mode toggle', async ({ page }) => {
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		await page.locator('button', { hasText: 'Edit' }).click();
		// Should see a toggle between Source and Rich Text modes
		await expect(
			page
				.locator('button', { hasText: 'Rich Text' })
				.or(page.locator('button', { hasText: 'Source' }))
		).toBeVisible({ timeout: 5000 });
	});
});
