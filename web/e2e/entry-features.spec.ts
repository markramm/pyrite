import { test, expect, type APIRequestContext } from '@playwright/test';

import { E2E_KB, SEEDED_PEOPLE, uniqueTitle, idForTitle } from './fixtures';
import { E2E_BACKEND_URL } from './global-setup';

/**
 * Entry detail page features: panel toggles, edit-mode switching, and the
 * source/rich-text editor toggle. Entry list, creation and the detail page's
 * read-only chrome belong to entry-crud.spec.ts.
 *
 * Panel-toggle tests exercise the UI-only `uiStore` panel state against a
 * seeded entry -- opening/closing a panel never writes to the entry itself.
 * The one test that actually SAVES an edit creates its own uniquely-titled
 * entry first: a seeded entry's body is shared, read-only material other
 * packages' specs may assert on in the same run, so this spec never edits one.
 */

// Per-worktree, not a hardcoded 8088 — see E2E_BACKEND_URL's own doc (#118).
const API_BASE = E2E_BACKEND_URL;

// See entry-crud.spec.ts for why this exists: a cold Vite dev server compiles
// a route's bundle on its first request, which can outrun the default 5s
// expect timeout under `fullyParallel` load. Used only for the first
// assertion after a `goto` to a route this spec hasn't warmed up yet.
const COLD_ROUTE_TIMEOUT = 15000;

async function createEntry(
	request: APIRequestContext,
	title: string,
	body: string
): Promise<string> {
	const res = await request.post(`${API_BASE}/api/entries`, {
		data: { kb: E2E_KB, entry_type: 'note', title, body }
	});
	expect(res.ok(), `create ${title}`).toBeTruthy();
	return (await res.json()).id;
}

async function deleteEntry(request: APIRequestContext, id: string): Promise<void> {
	await request.delete(`${API_BASE}/api/entries/${encodeURIComponent(id)}?kb=${E2E_KB}`);
}

test.describe('Entry Detail Page: panels', () => {
	// A seeded entry -- these tests only toggle UI panel state, never save.
	const seeded = SEEDED_PEOPLE[0];

	test('shows outline and backlinks toggle buttons', async ({ page }) => {
		await page.goto(`/entries/${seeded.id}`);
		await expect(page.getByRole('button', { name: 'Toggle outline panel' })).toBeAttached({
			timeout: COLD_ROUTE_TIMEOUT
		});
		await expect(page.getByRole('button', { name: 'Toggle backlinks panel' })).toBeAttached();
	});

	test('outline button toggles the outline panel', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto(`/entries/${seeded.id}`);
		const outlineBtn = page.getByRole('button', { name: 'Toggle outline panel' });
		await expect(outlineBtn).toBeVisible();

		await outlineBtn.click();
		await expect(outlineBtn).toHaveClass(/border-blue-500/);

		await outlineBtn.click();
		await expect(outlineBtn).not.toHaveClass(/border-blue-500/);
	});

	test('backlinks button toggles the backlinks panel', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto(`/entries/${seeded.id}`);
		const backlinksBtn = page.getByRole('button', { name: 'Toggle backlinks panel' });
		await expect(backlinksBtn).toBeVisible();

		await backlinksBtn.click();
		await expect(backlinksBtn).toHaveClass(/border-blue-500/);

		await backlinksBtn.click();
		await expect(backlinksBtn).not.toHaveClass(/border-blue-500/);
	});

	test('version history button toggles the version history panel', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto(`/entries/${seeded.id}`);
		const historyBtn = page.getByRole('button', { name: 'Toggle version history' });
		await expect(historyBtn).toBeVisible();

		await historyBtn.click();
		await expect(historyBtn).toHaveClass(/border-blue-500/);

		await historyBtn.click();
		await expect(historyBtn).not.toHaveClass(/border-blue-500/);
	});

	test('local graph button toggles the local graph panel', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto(`/entries/${seeded.id}`);
		const graphBtn = page.getByRole('button', { name: 'Toggle local graph' });
		await expect(graphBtn).toBeVisible();

		await graphBtn.click();
		await expect(graphBtn).toHaveClass(/border-blue-500/);

		await graphBtn.click();
		await expect(graphBtn).not.toHaveClass(/border-blue-500/);
	});

	// EntryMeta renders twice (mobile <details> + desktop <aside>, both always
	// in the DOM -- see entry-crud.spec.ts for the full explanation); the
	// `entry-meta-desktop` testid picks the one visible at this viewport.
	test('metadata sidebar shows the entry id and file path', async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 720 });
		await page.goto(`/entries/${seeded.id}`);
		const meta = page.getByTestId('entry-meta-desktop');
		await expect(meta.getByText(`ID: ${seeded.id}`, { exact: true })).toBeVisible({
			timeout: COLD_ROUTE_TIMEOUT
		});
		await expect(meta.getByText(/^File: /)).toBeVisible();
	});
});

test.describe('Entry Detail Page: editing', () => {
	test('edit button switches to editor mode and back', async ({ page, request }) => {
		const title = uniqueTitle('E2E Features Edit Toggle');
		const id = idForTitle(title);
		try {
			await createEntry(request, title, 'Original body.');
			await page.goto(`/entries/${id}`);

			const editBtn = page.getByRole('button', { name: 'Edit' });
			await expect(editBtn).toBeVisible();
			await editBtn.click();

			await expect(page.getByRole('button', { name: 'View' })).toBeVisible();
			await expect(page.getByRole('button', { name: 'Save' })).toBeVisible();

			// Back to the read view without saving -- the entry is untouched.
			await page.getByRole('button', { name: 'View' }).click();
			await expect(page.getByRole('button', { name: 'Edit' })).toBeVisible();
		} finally {
			await deleteEntry(request, id);
		}
	});

	test('edit mode shows the Source/Rich Text editor-mode toggle, defaulting to source', async ({
		page,
		request
	}) => {
		const title = uniqueTitle('E2E Features Editor Mode');
		const id = idForTitle(title);
		try {
			await createEntry(request, title, 'Body for editor-mode toggle test.');
			await page.goto(`/entries/${id}`);
			await page.getByRole('button', { name: 'Edit' }).click();

			// Default mode is 'source' (web/src/lib/stores/ui.svelte.ts); the
			// toggle button's own label names the mode it would switch TO.
			const modeToggle = page.getByRole('button', { name: 'Rich Text' });
			await expect(modeToggle).toBeVisible();

			await modeToggle.click();
			await expect(page.getByRole('button', { name: 'Source' })).toBeVisible();
		} finally {
			await deleteEntry(request, id);
		}
	});

	test('editing and saving persists the new body to a freshly created entry', async ({
		page,
		request
	}) => {
		const title = uniqueTitle('E2E Features Save');
		const id = idForTitle(title);
		const updatedBody = `Updated by entry-features.spec.ts at ${Date.now()}.`;
		try {
			await createEntry(request, title, 'Original body, about to be replaced.');
			await page.goto(`/entries/${id}`);
			await page.getByRole('button', { name: 'Edit' }).click();

			// Source mode (the default) is CodeMirror, not a native <textarea>;
			// select-all + type replaces the document instead of appending.
			const editorContent = page.locator('.cm-content');
			await editorContent.click();
			await editorContent.press('ControlOrMeta+a');
			await editorContent.press('Delete');
			await editorContent.pressSequentially(updatedBody);

			// save() (web/src/routes/entries/[id]/+page.svelte) does not flip
			// `editing` back to false -- it stays in edit mode after a save, on
			// the reasoning that you likely want to keep editing. The toolbar
			// therefore still reads "View"/"Save" afterwards, not "Edit"; this
			// waits for the save round-trip via the Save button's own disabled
			// state rather than asserting a button label the app never shows.
			const saveBtn = page.getByRole('button', { name: 'Save' });
			await saveBtn.click();
			await expect(saveBtn).toBeEnabled();
			await expect(page.getByRole('button', { name: 'View' })).toBeVisible();

			const res = await request.get(`${API_BASE}/api/entries/${id}?kb=${E2E_KB}`);
			expect(res.ok()).toBeTruthy();
			expect((await res.json()).body).toBe(updatedBody);
		} finally {
			await deleteEntry(request, id);
		}
	});
});
