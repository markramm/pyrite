import { test, expect } from '@playwright/test';

import { E2E_BACKEND_URL } from './global-setup';

test.describe('Graph Page', () => {
	test('navigates to graph page and shows title', async ({ page }) => {
		await page.goto('/graph');
		// The Topbar's title has no heading role (it's a <span>, shared across
		// every route) — data-testid="page-title" added to
		// web/src/lib/components/layout/Topbar.svelte.
		await expect(page.getByTestId('page-title')).toHaveText('Knowledge Graph');
	});

	test('shows graph controls', async ({ page }) => {
		await page.goto('/graph');
		await expect(page.getByLabel('KB')).toBeVisible();
		await expect(page.getByLabel('Type')).toBeVisible();
		await expect(page.locator('input[type="range"]')).toBeVisible();
		await expect(page.getByLabel('Layout')).toBeVisible();
		await expect(page.getByRole('button', { name: 'Fit' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Reset Layout' })).toBeVisible();
	});

	test('graph API endpoint responds with nodes/edges shape for the seeded world', async ({ request }) => {
		// Per-worktree, not a hardcoded 8088 — see E2E_BACKEND_URL's own doc (#118).
		const response = await request.get(`${E2E_BACKEND_URL}/api/graph`);
		expect(response.ok()).toBeTruthy();
		const data = await response.json();
		expect(data).toHaveProperty('nodes');
		expect(data).toHaveProperty('edges');
		expect(Array.isArray(data.nodes)).toBeTruthy();
		expect(Array.isArray(data.edges)).toBeTruthy();
		// The seeded world (global-setup.ts) creates no `--link`s between entries
		// and no wikilinks in entry bodies, so the graph is empty by construction —
		// see the report filed against this ticket for restoring seeded links.
		expect(data.nodes).toEqual([]);
		expect(data.edges).toEqual([]);
	});

	test('shows the empty-graph state because the seeded world has no linked entries', async ({ page }) => {
		await page.goto('/graph');
		// Deterministic, not a dodge: the seed creates zero links (confirmed via
		// /api/graph above), so this is the only state the page can reach today.
		await expect(page.getByText('No linked entries found.')).toBeVisible({ timeout: 10000 });
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

	test('layout selector has the four seeded layout options', async ({ page }) => {
		await page.goto('/graph');
		const layoutSelect = page.getByLabel('Layout');
		await expect(layoutSelect).toBeVisible();
		await expect(layoutSelect.locator('option')).toHaveCount(4);
		await expect(layoutSelect.locator('option')).toHaveText([
			'Force-directed',
			'Circle',
			'Grid',
			'Concentric'
		]);
	});

	test('depth slider is interactive', async ({ page }) => {
		await page.goto('/graph');
		const slider = page.locator('input[type="range"]');
		await expect(slider).toBeVisible();
		await expect(slider).toHaveAttribute('min', '1');
		await expect(slider).toHaveAttribute('max', '3');
	});

	test('type filter dropdown has All plus the seeded world entry types', async ({ page }) => {
		await page.goto('/graph');
		const typeSelect = page.getByLabel('Type');
		await expect(typeSelect).toBeVisible();
		// Default value is "All" (empty option value).
		await expect(typeSelect).toHaveValue('');
		// The seeded world (global-setup.ts) creates exactly these five entry
		// types — collection, event, note, organization, person — confirmed
		// against GET /api/entries/types.
		await expect(typeSelect.locator('option')).toHaveText([
			'All',
			'collection',
			'event',
			'note',
			'organization',
			'person'
		]);
	});

	test('entry types API endpoint returns the seeded world types', async ({ request }) => {
		const response = await request.get(`${E2E_BACKEND_URL}/api/entries/types`);
		expect(response.ok()).toBeTruthy();
		const data = await response.json();
		expect(data).toHaveProperty('types');
		expect(data.types.sort()).toEqual(['collection', 'event', 'note', 'organization', 'person']);
	});
});

test.describe('Local Graph Panel', () => {
	// Navigate straight to a seeded person entry rather than through the
	// /entries list — the list view is out of this package's scope and its
	// default rendering doesn't guarantee a stable `a[href^="/entries/"]`
	// target. e2e-person-ada-lovelace is seeded by global-setup.ts.
	const SEEDED_ENTRY_PATH = '/entries/e2e-person-ada-lovelace';

	test('entry page has a local-graph toggle button', async ({ page }) => {
		await page.goto(SEEDED_ENTRY_PATH);
		await expect(page.getByRole('button', { name: 'Toggle local graph' })).toBeVisible();
	});

	test('local-graph toggle opens and closes the panel, which shows no linked entries', async ({ page }) => {
		await page.goto(SEEDED_ENTRY_PATH);
		const graphBtn = page.getByRole('button', { name: 'Toggle local graph' });
		await expect(graphBtn).toBeVisible();

		// Closed state: not the active/open styling.
		await expect(graphBtn).not.toHaveClass(/border-blue-500/);

		await graphBtn.click();
		await expect(graphBtn).toHaveClass(/border-blue-500/);
		await expect(page.getByRole('heading', { name: 'Local Graph' })).toBeVisible();
		// Deterministic given the seeded world has no links (see the graph API
		// assertions above) — not a "some data or empty state" dodge.
		await expect(page.getByText('No linked entries')).toBeVisible();

		await graphBtn.click();
		await expect(graphBtn).not.toHaveClass(/border-blue-500/);
	});
});
