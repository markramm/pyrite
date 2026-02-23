import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
	test('loads and shows Pyrite branding', async ({ page }) => {
		await page.goto('/');
		await expect(page.getByRole('link', { name: 'Pyrite', exact: true })).toBeVisible();
	});

	test('shows dashboard heading', async ({ page }) => {
		await page.goto('/');
		await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
	});

	test('displays stat cards', async ({ page }) => {
		await page.goto('/');
		await expect(page.getByRole('heading', { name: 'Knowledge Bases' })).toBeVisible();
		await expect(page.locator('.text-sm:has-text("Total Entries")')).toBeVisible();
	});
});

test.describe('Sidebar Navigation', () => {
	test('sidebar has navigation links', async ({ page }) => {
		await page.goto('/');
		const sidebar = page.locator('aside');
		await expect(sidebar.locator('text=Entries')).toBeVisible();
		await expect(sidebar.locator('text=Graph')).toBeVisible();
		await expect(sidebar.locator('text=Timeline')).toBeVisible();
		await expect(sidebar.locator('text=Daily Notes')).toBeVisible();
	});

	test('navigates to entries page', async ({ page }) => {
		await page.goto('/');
		await page.click('aside >> text=Entries');
		await expect(page).toHaveURL(/\/entries/);
		await expect(page.getByRole('heading', { name: 'Entries' })).toBeVisible();
	});

	test('navigates to timeline page', async ({ page }) => {
		await page.goto('/');
		await page.click('aside >> text=Timeline');
		await expect(page).toHaveURL(/\/timeline/);
		await expect(page.getByRole('heading', { name: 'Timeline' })).toBeVisible();
	});

	test('navigates to graph page', async ({ page }) => {
		await page.goto('/');
		await page.click('aside >> text=Graph');
		await expect(page).toHaveURL(/\/graph/);
	});
});

test.describe('Entries Page', () => {
	test('shows entry list or empty state', async ({ page }) => {
		await page.goto('/entries');
		// Either shows entries or "No entries found"
		await expect(
			page.locator('text=No entries found').or(page.locator('[href^="/entries/"]').first())
		).toBeVisible({ timeout: 5000 });
	});

	test('has type filter dropdown', async ({ page }) => {
		await page.goto('/entries');
		const select = page.locator('select');
		await expect(select.first()).toBeVisible();
	});

	test('has search input', async ({ page }) => {
		await page.goto('/entries');
		await expect(page.locator('input[type="search"]')).toBeVisible();
	});

	test('has new entry button', async ({ page }) => {
		await page.goto('/entries');
		await expect(page.locator('text=New Entry')).toBeVisible();
	});
});

test.describe('Theme Toggle', () => {
	test('page starts in dark mode', async ({ page }) => {
		await page.goto('/');
		const html = page.locator('html');
		await expect(html).toHaveClass(/dark/);
	});

	test('toggles between dark and light mode', async ({ page }) => {
		await page.goto('/');
		const html = page.locator('html');
		await expect(html).toHaveClass(/dark/);

		// Click theme toggle button (in sidebar header)
		await page.click('aside button[title="Toggle theme"]');
		await expect(html).not.toHaveClass(/dark/);

		// Toggle back
		await page.click('aside button[title="Toggle theme"]');
		await expect(html).toHaveClass(/dark/);
	});
});

test.describe('API Health', () => {
	test('backend health endpoint responds', async ({ request }) => {
		const response = await request.get('http://localhost:8088/health');
		expect(response.ok()).toBeTruthy();
		const data = await response.json();
		expect(data.status).toBe('ok');
	});

	test('API kbs endpoint responds', async ({ request }) => {
		const response = await request.get('http://localhost:8088/api/kbs');
		expect(response.ok()).toBeTruthy();
		const data = await response.json();
		expect(data).toHaveProperty('kbs');
		expect(data).toHaveProperty('total');
	});
});
