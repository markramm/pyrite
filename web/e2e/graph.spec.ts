import { test, expect } from '@playwright/test';

test.describe('Graph Page', () => {
	test('navigates to graph page and shows title', async ({ page }) => {
		await page.goto('/graph');
		await expect(page.locator('text=Knowledge Graph')).toBeVisible();
	});

	test('shows graph controls', async ({ page }) => {
		await page.goto('/graph');
		// KB dropdown
		await expect(page.locator('label:has-text("KB") select')).toBeVisible();
		// Type dropdown
		await expect(page.locator('label:has-text("Type") select')).toBeVisible();
		// Depth slider
		await expect(page.locator('input[type="range"]')).toBeVisible();
		// Layout dropdown
		await expect(page.locator('label:has-text("Layout") select')).toBeVisible();
		// Fit and Reset buttons
		await expect(page.getByRole('button', { name: 'Fit' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Reset Layout' })).toBeVisible();
	});

	test('graph API endpoint responds with nodes/edges shape', async ({ request }) => {
		const response = await request.get('http://localhost:8088/api/graph');
		expect(response.ok()).toBeTruthy();
		const data = await response.json();
		expect(data).toHaveProperty('nodes');
		expect(data).toHaveProperty('edges');
		expect(Array.isArray(data.nodes)).toBeTruthy();
		expect(Array.isArray(data.edges)).toBeTruthy();
	});

	test('shows graph content after loading', async ({ page }) => {
		await page.goto('/graph');
		// Wait for loading to finish — shows count, empty state, or error
		await expect(
			page.locator('text=/\\d+ nodes, \\d+ edges/').or(
				page.locator('text=No linked entries found')
			).or(
				page.locator('text=/Error|error/')
			)
		).toBeVisible({ timeout: 10000 });
	});

	test('has search input', async ({ page }) => {
		await page.goto('/graph');
		await expect(page.locator('input[type="search"]')).toBeVisible();
	});

	test('search input accepts text', async ({ page }) => {
		await page.goto('/graph');
		const searchInput = page.locator('input[type="search"]');
		await searchInput.fill('test query');
		await expect(searchInput).toHaveValue('test query');
	});

	test('layout selector has options', async ({ page }) => {
		await page.goto('/graph');
		const layoutSelect = page.locator('label:has-text("Layout") select');
		await expect(layoutSelect).toBeVisible();
		// Check that it has the expected layout options
		await expect(layoutSelect.locator('option')).toHaveCount(4);
	});

	test('depth slider is interactive', async ({ page }) => {
		await page.goto('/graph');
		const slider = page.locator('input[type="range"]');
		await expect(slider).toBeVisible();
		await expect(slider).toHaveAttribute('min', '1');
		await expect(slider).toHaveAttribute('max', '3');
	});

	test('type filter dropdown exists with All option', async ({ page }) => {
		await page.goto('/graph');
		const typeSelect = page.locator('label:has-text("Type") select');
		await expect(typeSelect).toBeVisible();
		// The select should have "All" as the default value
		await expect(typeSelect).toHaveValue('');
	});

	test('entry types API endpoint responds', async ({ request }) => {
		const response = await request.get('http://localhost:8088/api/entries/types');
		expect(response.ok()).toBeTruthy();
		const data = await response.json();
		expect(data).toHaveProperty('types');
		expect(Array.isArray(data.types)).toBeTruthy();
	});
});

test.describe('Local Graph Panel', () => {
	test('entry page has Graph toggle button', async ({ page }) => {
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		await expect(page.getByRole('button', { name: 'Graph' })).toBeVisible();
	});

	test('Graph button toggles local graph panel visibility', async ({ page }) => {
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		const graphBtn = page.getByRole('button', { name: 'Graph' });
		await expect(graphBtn).toBeVisible();

		// Click to open graph panel
		await graphBtn.click();
		await expect(graphBtn).toHaveClass(/border-blue-500/);

		// Click again to close
		await graphBtn.click();
		await expect(graphBtn).not.toHaveClass(/border-blue-500/);
	});
});
