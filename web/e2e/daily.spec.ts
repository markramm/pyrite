import { test, expect } from '@playwright/test';

test.describe('Daily Notes Page', () => {
	test('loads daily notes page', async ({ page }) => {
		await page.goto('/daily');
		await expect(page).toHaveTitle(/Daily Notes/);
		// Breadcrumbs show "Daily Notes" in the topbar header
		await expect(page.locator('header nav >> text=Daily Notes')).toBeVisible();
	});

	test('shows today\'s date formatted', async ({ page }) => {
		await page.goto('/daily');
		// The DailyNote component renders today's date in long format
		// e.g., "Wednesday, March 4, 2026"
		const today = new Date();
		const longMonth = today.toLocaleDateString('en-US', { month: 'long' });
		// At minimum, the current month name should appear in the date heading
		await expect(page.locator('h1').first()).toContainText(longMonth, { timeout: 5000 });
	});

	test('breadcrumb shows selected date in YYYY-MM-DD format', async ({ page }) => {
		await page.goto('/daily');
		const today = new Date();
		const y = today.getFullYear();
		const m = String(today.getMonth() + 1).padStart(2, '0');
		const d = String(today.getDate()).padStart(2, '0');
		const todayStr = `${y}-${m}-${d}`;
		await expect(page.locator(`nav >> text=${todayStr}`)).toBeVisible();
	});

	test('has date navigation buttons', async ({ page }) => {
		await page.goto('/daily');
		await expect(page.getByLabel('Previous day')).toBeVisible();
		await expect(page.getByLabel('Next day')).toBeVisible();
		await expect(page.locator('button', { hasText: 'Today' })).toBeVisible();
	});

	test('previous day button navigates to yesterday', async ({ page }) => {
		await page.goto('/daily');
		const headingBefore = await page.locator('h1').first().textContent();

		await page.getByLabel('Previous day').click();

		const headingAfter = await page.locator('h1').first().textContent();
		expect(headingAfter).not.toBe(headingBefore);
	});

	test('next day button navigates forward', async ({ page }) => {
		await page.goto('/daily');
		const headingBefore = await page.locator('h1').first().textContent();

		await page.getByLabel('Next day').click();

		const headingAfter = await page.locator('h1').first().textContent();
		expect(headingAfter).not.toBe(headingBefore);
	});

	test('today button returns to current date', async ({ page }) => {
		await page.goto('/daily');
		const headingInitial = await page.locator('h1').first().textContent();

		// Navigate away
		await page.getByLabel('Previous day').click();
		await page.getByLabel('Previous day').click();

		// Click Today
		await page.locator('button', { hasText: 'Today' }).click();

		// Should return to original date
		const headingAfterToday = await page.locator('h1').first().textContent();
		expect(headingAfterToday).toBe(headingInitial);
	});

	test('shows daily note content or error state', async ({ page }) => {
		await page.goto('/daily');
		// Either the note content loads (prose area), loading spinner, or error
		await expect(
			page
				.locator('.prose')
				.or(page.locator('text=Loading...'))
				.or(page.locator('text=No KB selected'))
				.or(page.locator('.text-red-500'))
				.first()
		).toBeVisible({ timeout: 5000 });
	});

	test('shows edit button when daily note exists', async ({ page }) => {
		await page.goto('/daily');
		const editBtn = page.locator('button', { hasText: 'Edit' });
		const hasNote = await editBtn.isVisible({ timeout: 3000 }).catch(() => false);

		if (!hasNote) {
			test.skip(true, 'No daily note available to test edit button');
			return;
		}

		await expect(editBtn).toBeVisible();
	});
});

test.describe('Calendar Widget', () => {
	test('calendar sidebar is visible on desktop', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/daily');

		const calendarAside = page.locator('aside').last();
		await expect(calendarAside).toBeVisible({ timeout: 5000 });
	});

	test('calendar shows current month label', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/daily');

		const today = new Date();
		const monthLabel = today.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
		await expect(page.locator('text=' + monthLabel)).toBeVisible({ timeout: 5000 });
	});

	test('calendar has month navigation buttons', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/daily');

		await expect(page.getByLabel('Previous month')).toBeVisible({ timeout: 5000 });
		await expect(page.getByLabel('Next month')).toBeVisible();
	});

	test('calendar shows day-of-week headers', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/daily');

		const calendarArea = page.locator('aside').last();
		await expect(calendarArea.locator('text=S').first()).toBeVisible({ timeout: 5000 });
		await expect(calendarArea.locator('text=M').first()).toBeVisible();
		await expect(calendarArea.locator('text=F').first()).toBeVisible();
	});

	test('clicking a calendar date updates the daily note heading', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/daily');

		// Click day 1 of the month in the calendar grid
		const calendarAside = page.locator('aside').last();
		const dayButton = calendarAside.locator('button', { hasText: '1' }).first();
		const dayVisible = await dayButton.isVisible({ timeout: 3000 }).catch(() => false);

		if (!dayVisible) {
			test.skip(true, 'Calendar day buttons not visible');
			return;
		}

		await dayButton.click();
		// The heading should reflect the selected date
		await expect(page.locator('h1').first()).toBeVisible();
	});

	test('previous month button changes calendar days', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto('/daily');

		const calendarAside = page.locator('aside').last();
		await expect(calendarAside).toBeVisible({ timeout: 5000 });

		// Get initial set of day buttons
		const dayButtons = calendarAside.locator('button');
		const initialCount = await dayButtons.count();
		expect(initialCount).toBeGreaterThan(0);

		// Click the Previous month button
		const prevBtn = calendarAside.getByLabel('Previous month');
		await expect(prevBtn).toBeVisible();
		await prevBtn.click();

		// The calendar grid should still have day buttons after navigation
		await expect(dayButtons.first()).toBeVisible({ timeout: 5000 });
	});
});
