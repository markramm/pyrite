import { test, expect } from '@playwright/test';

test.describe('Entries Page', () => {
	test('entries page loads with list or empty state', async ({ page }) => {
		await page.goto('/entries');
		await expect(page.getByRole('heading', { name: 'Entries' }).first()).toBeVisible();
		// Either shows entries or the empty state
		await expect(
			page.locator('text=No entries found').or(page.locator('a[href^="/entries/"]').first())
		).toBeVisible({ timeout: 5000 });
	});

	test('has type filter dropdown with "All types" default', async ({ page }) => {
		await page.goto('/entries');
		const select = page.locator('select');
		await expect(select.first()).toBeVisible();
		await expect(select.first()).toContainText('All types');
	});

	test('has sort controls', async ({ page }) => {
		await page.goto('/entries');
		// Sort-by dropdown with options
		const sortSelect = page.locator('select').first();
		await expect(sortSelect).toBeVisible();
		await expect(sortSelect).toContainText('Updated');
		// Sort direction toggle button
		await expect(page.getByLabel('Toggle sort direction')).toBeVisible();
	});

	test('has search input', async ({ page }) => {
		await page.goto('/entries');
		await expect(page.locator('input[type="search"]')).toBeVisible();
		await expect(page.locator('input[type="search"]')).toHaveAttribute('placeholder', 'Search...');
	});

	test('has new entry button linking to creation page', async ({ page }) => {
		await page.goto('/entries');
		const newBtn = page.locator('a', { hasText: 'New Entry' });
		await expect(newBtn).toBeVisible();
		await expect(newBtn).toHaveAttribute('href', '/entries/new');
	});
});

test.describe('New Entry Page', () => {
	test('new entry button navigates to creation form', async ({ page }) => {
		await page.goto('/entries');
		await page.click('a:has-text("New Entry")');
		await expect(page).toHaveURL(/\/entries\/new/);
		await expect(page.getByRole('heading', { name: 'New Entry' })).toBeVisible();
	});

	test('creation form has title input', async ({ page }) => {
		await page.goto('/entries/new');
		await expect(page.getByLabel('Title')).toBeVisible();
		await expect(page.locator('input#entry-title')).toHaveAttribute(
			'placeholder',
			'Entry title...'
		);
	});

	test('creation form shows template picker', async ({ page }) => {
		await page.goto('/entries/new');
		// Template section heading
		await expect(page.getByRole('heading', { name: 'Choose a template' })).toBeVisible();
	});

	test('can fill in entry title', async ({ page }) => {
		await page.goto('/entries/new');
		const titleInput = page.locator('input#entry-title');
		await titleInput.fill('Test Entry Title');
		await expect(titleInput).toHaveValue('Test Entry Title');
	});

	test('breadcrumbs show entries link and new entry label', async ({ page }) => {
		await page.goto('/entries/new');
		// Breadcrumb should have link back to Entries
		await expect(page.locator('a[href="/entries"]', { hasText: 'Entries' })).toBeVisible();
		// And show "New Entry" as current breadcrumb
		await expect(page.locator('text=New Entry').first()).toBeVisible();
	});
});

test.describe('Entry Detail Page', () => {
	test('entry detail page shows title and body', async ({ page }) => {
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		await expect(page.locator('h1').first()).toBeVisible();
		// Entry should have a prose content area or editor area
		await expect(
			page.locator('.prose').or(page.locator('text=Loading...')).first()
		).toBeVisible({ timeout: 5000 });
	});

	test('entry detail has edit button', async ({ page }) => {
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		// Edit button is present in the toolbar
		await expect(
			page.locator('button', { hasText: 'Edit' })
		).toBeVisible({ timeout: 5000 });
	});

	test('entry detail shows metadata sidebar', async ({ page }) => {
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

	test('star button is present on entry detail', async ({ page }) => {
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		// StarButton is rendered in the toolbar next to the title
		// It renders as a button with a star SVG
		const starBtn = page.locator('button').filter({ has: page.locator('svg') }).first();
		await expect(starBtn).toBeVisible({ timeout: 5000 });
	});

	test('entry detail has panel toggle buttons', async ({ page }) => {
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		// Panel toggle buttons (visible on large screens, hidden on mobile)
		await expect(page.getByLabel('Toggle outline panel')).toBeAttached();
		await expect(page.getByLabel('Toggle backlinks panel')).toBeAttached();
		await expect(page.getByLabel('Toggle version history')).toBeAttached();
		await expect(page.getByLabel('Toggle local graph')).toBeAttached();
	});

	test('entry detail has breadcrumb navigation', async ({ page }) => {
		await page.goto('/entries');
		const firstEntry = page.locator('a[href^="/entries/"]').first();
		const hasEntries = await firstEntry.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasEntries) {
			test.skip(true, 'No entries available to test');
			return;
		}

		await firstEntry.click();
		// Breadcrumb should have "Entries" link
		await expect(page.locator('a[href="/entries"]', { hasText: 'Entries' })).toBeVisible({
			timeout: 5000
		});
	});
});
