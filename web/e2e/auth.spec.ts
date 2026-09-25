/**
 * The login and registration surface, against a backend where auth is ON.
 *
 * # The decision this file records (Package C)
 *
 * Package A built the e2e world with `PYRITE_AUTH_ENABLED=false`, which makes
 * `verify_api_key` resolve every caller to `admin`, and left the auth specs an
 * explicit choice (`fixtures.ts`): skip them under that world, or run them
 * under their own auth-enabled project. **This file takes the second option.**
 *
 * The reason is that under the auth-disabled world these tests assert nothing.
 * `/login` still renders — it is a route with a form — but nothing is behind
 * it: `POST /auth/login` returns `400 "Authentication is not enabled"`
 * (`auth_endpoints.py`), the root layout's gate
 * (`authStore.authConfig.enabled && !isAuthenticated` in `+layout.svelte`)
 * never fires, so no redirect to `/login` ever happens and no redirect away
 * from it after login ever happens either. A spec there can assert that a
 * username input exists and that typing into it works — which is a test of
 * markup, not of the login path. 0.24.2's definition of done is that every
 * user surface has an end-to-end test, and the surface here is "a real
 * deployment's users log in", not "the login form has two inputs".
 *
 * So the specs below run under the `chromium-auth` project, against a second
 * backend with `auth.enabled: true`, a second data directory, a second port
 * and a second Vite dev server. The machinery and the reason each piece is
 * separate are documented in `e2e/auth-setup.ts`; the user is created by
 * `e2e/auth.setup.ts`. `playwright.config.ts` was extended additively: the
 * existing `chromium` project gained a `testIgnore` for this file and nothing
 * else about it changed.
 *
 * What that buys, concretely — every one of these is false under the
 * auth-disabled world and true here:
 *
 *   - an unauthenticated visit to an app route is redirected to `/login`;
 *   - wrong credentials produce the API's real 401 and a visible error;
 *   - correct credentials produce a session and land the user in the app;
 *   - a logged-in user visiting `/login` is redirected out of it;
 *   - the register link appears because the server says registration is
 *     allowed, not because the markup always contains it.
 *
 * # Locator rules (this package's acceptance criteria)
 *
 * No `text=` locators; role, label and href only, plus one `data-testid` where
 * neither exists (see `login-error`/`register-error` below). No `.first()`.
 *
 * # A product bug this project found and fixed
 *
 * Asserting on the real error text — which only an auth-enabled world can
 * produce — showed that both forms rendered `ApiError.message`, the
 * developer-facing string, so a person mistyping their password read
 * "API Error 401: Invalid username or password". `ApiError` already carries
 * `.detail` (the server's own message) for exactly this; both routes now use
 * it. A one-line fix inside this package's footprint, so it is fixed rather
 * than `test.fixme`d. Under the auth-disabled world this was unreachable: the
 * submission never gets far enough to produce a 401.
 */
import { test, expect, type APIRequestContext, type Page } from '@playwright/test';

import { AUTH_BACKEND_URL, AUTH_E2E_KB, SEEDED_USER, UNKNOWN_USER } from './auth-setup';

/**
 * Log in through the form, the way a user does.
 *
 * Not an API call with a cookie injected: the point of this project is that
 * the browser path works, and a helper that bypassed the form would make the
 * post-login assertions vacuous.
 */
async function loginAs(page: Page, username: string, password: string): Promise<void> {
	await page.goto('/login');
	await page.getByLabel('Username').fill(username);
	await page.getByLabel('Password').fill(password);
	await page.getByRole('button', { name: 'Sign in' }).click();
}

test.describe('Auth is enabled in this project', () => {
	// The guard for every other test in the file. If this fails, the project is
	// pointed at the wrong backend and every assertion below is meaningless
	// (and several would still pass, which is exactly the failure mode this
	// package exists to remove).
	test('the backend this project talks to reports auth enabled', async ({ page }) => {
		const response = await page.request.get('/auth/config');
		expect(response.ok()).toBeTruthy();
		const config = await response.json();
		expect(config.enabled).toBe(true);
		expect(config.allow_registration).toBe(true);
		expect(config.anonymous_tier).toBe('none');
	});
});

test.describe('The auth gate', () => {
	test('an unauthenticated visit to an app route is sent to /login', async ({ page }) => {
		// `/entries` is an ordinary app route, not an auth route. With auth on
		// and no session, +layout.svelte's onMount gate redirects.
		await page.goto('/entries');
		await expect(page).toHaveURL(/\/login$/);
		await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
	});

	test('the API refuses an unauthenticated request', async ({ page }) => {
		// The other half of the same contract: the gate is a convenience, the
		// 401 is the enforcement. Under the auth-disabled world this is a 200.
		const response = await page.request.get('/api/kbs');
		expect(response.status()).toBe(401);
	});
});

test.describe('Login page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/login');
	});

	test('shows the brand heading and the sign-in prompt', async ({ page }) => {
		// The login route renders outside the app shell (+layout.svelte's
		// AUTH_ROUTES branch), so its <h1> is the only level-1 heading on the
		// page — no sidebar logo to collide with, hence no scoping needed and
		// no `.first()`.
		await expect(page.getByRole('heading', { level: 1 })).toHaveText('Pyrite');
		await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
	});

	test('has a required username field', async ({ page }) => {
		const username = page.getByLabel('Username');
		await expect(username).toBeVisible();
		await expect(username).toHaveAttribute('type', 'text');
		await expect(username).toHaveAttribute('required', '');
	});

	test('has a required password field', async ({ page }) => {
		const password = page.getByLabel('Password');
		await expect(password).toBeVisible();
		await expect(password).toHaveAttribute('type', 'password');
		await expect(password).toHaveAttribute('required', '');
	});

	test('links to registration because the server allows it', async ({ page }) => {
		// The link is rendered only when `authConfig.allow_registration` is
		// true, and this world's backend sets it true explicitly
		// (AUTH_E2E_ENV) — so this asserts on the seeded world's contract, not
		// on "the link may or may not be there".
		const registerLink = page.getByRole('link', { name: 'Register' });
		await expect(registerLink).toHaveAttribute('href', '/register');
	});
});

test.describe('Signing in', () => {
	test('wrong credentials leave the user on /login with an error', async ({ page }) => {
		await loginAs(page, UNKNOWN_USER.username, UNKNOWN_USER.password);

		// The message is the API's own 401 detail, surfaced by the auth store.
		// Under the auth-disabled world the same submission fails with
		// "Authentication is not enabled" instead — a different world, a
		// different message, which is the point.
		await expect(page.getByTestId('login-error')).toHaveText('Invalid username or password');
		await expect(page).toHaveURL(/\/login$/);
	});

	test('the right credentials sign the user in and land them in the app', async ({ page }) => {
		await loginAs(page, SEEDED_USER.username, SEEDED_USER.password);

		// The login handler navigates to `/` on success; arriving there with the
		// app shell rendered (rather than being bounced back to /login by the
		// gate) is the proof that the session cookie was set and accepted.
		await expect(page).toHaveURL(/localhost:\d+\/$/);
		await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible();
	});

	test('a signed-in user is redirected away from /login', async ({ page }) => {
		await loginAs(page, SEEDED_USER.username, SEEDED_USER.password);
		await expect(page).toHaveURL(/localhost:\d+\/$/);

		// Second half of the gate in +layout.svelte: enabled && authenticated &&
		// on an auth route -> goto('/').
		await page.goto('/login');
		await expect(page).toHaveURL(/localhost:\d+\/$/);
	});

	test('a signed-in user can reach an app route the gate refused before', async ({ page }) => {
		await loginAs(page, SEEDED_USER.username, SEEDED_USER.password);
		await expect(page).toHaveURL(/localhost:\d+\/$/);

		await page.goto('/entries');
		await expect(page).toHaveURL(/\/entries$/);
		await expect(page.getByRole('heading', { name: 'Entries', level: 1 })).toHaveCount(1);
	});
});

test.describe('Register page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/register');
	});

	test('shows the brand heading and the create-account action', async ({ page }) => {
		await expect(page.getByRole('heading', { level: 1 })).toHaveText('Pyrite');
		await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible();
	});

	test('has the four account fields with their required-ness', async ({ page }) => {
		const username = page.getByLabel('Username');
		await expect(username).toHaveAttribute('required', '');

		// Display name is the only optional one; its label says so.
		const displayName = page.getByLabel('Display Name (optional)');
		await expect(displayName).toBeVisible();
		await expect(displayName).not.toHaveAttribute('required', '');

		// `Password` and `Confirm Password` are distinct accessible names, so
		// an exact match keeps each a single element without `.first()`.
		const password = page.getByLabel('Password', { exact: true });
		await expect(password).toHaveAttribute('type', 'password');
		await expect(password).toHaveAttribute('required', '');
		// The API enforces 8 characters; the form declares the same minimum.
		await expect(password).toHaveAttribute('minlength', '8');

		const confirm = page.getByLabel('Confirm Password');
		await expect(confirm).toHaveAttribute('type', 'password');
		await expect(confirm).toHaveAttribute('required', '');
	});

	test('does not ask for an invite code, because this world does not require one', async ({
		page
	}) => {
		// Rendered only when `authConfig.require_invite_code`; the seeded world
		// leaves it at its default of false.
		await expect(page.getByLabel('Invite Code')).toHaveCount(0);
	});

	test('links back to the login page', async ({ page }) => {
		await expect(page.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');
	});

	test('mismatched passwords are rejected client-side', async ({ page }) => {
		await page.getByLabel('Username').fill('e2e-mismatch');
		await page.getByLabel('Password', { exact: true }).fill('e2e-password-123');
		await page.getByLabel('Confirm Password').fill('e2e-password-456');
		await page.getByRole('button', { name: 'Create account' }).click();

		await expect(page.getByTestId('register-error')).toHaveText('Passwords do not match');
		await expect(page).toHaveURL(/\/register$/);
	});

	test('a duplicate username is rejected by the server', async ({ page }) => {
		// SEEDED_USER already exists (auth.setup.ts registered it), so this
		// exercises the real server-side uniqueness check rather than a
		// client-side guess. It is also why this spec does not register a NEW
		// user: a successful registration auto-logs-in and mutates the shared
		// world, and the "first user is admin" invariant the setup depends on
		// must hold for the whole run.
		await page.getByLabel('Username').fill(SEEDED_USER.username);
		await page.getByLabel('Password', { exact: true }).fill('e2e-password-123');
		await page.getByLabel('Confirm Password').fill('e2e-password-123');
		await page.getByRole('button', { name: 'Create account' }).click();

		// The server's own message (`AuthService.register`), not a client-side
		// guess and not the developer-facing "API Error 400: ..." string.
		await expect(page.getByTestId('register-error')).toHaveText('Username already taken');
		await expect(page).toHaveURL(/\/register$/);
	});
});

test.describe('The live-update socket follows the signed-in user (#336)', () => {
	/**
	 * The server fixes a socket's readable KBs at handshake (#323). Before
	 * #336 the web client opened its socket once and kept it across a logout,
	 * so the login page went on toasting the previous user's new entries. In
	 * this world `anonymous_tier` is `none`: every KB is readable only by a
	 * signed-in user, so any event reaching a signed-out page is a leak.
	 */
	test('after logout through the sidebar, no event from the old scope reaches the page', async ({
		page,
		playwright
	}) => {
		// A writer outside the browser, with its own session: the "other tab"
		// whose writes the socket reports.
		const writer: APIRequestContext = await playwright.request.newContext({
			baseURL: AUTH_BACKEND_URL
		});
		try {
			const login = await writer.post('/auth/login', {
				data: { username: SEEDED_USER.username, password: SEEDED_USER.password }
			});
			expect(login.ok(), await login.text()).toBeTruthy();

			async function createEntry(title: string): Promise<string> {
				const res = await writer.post('/api/entries', {
					data: { kb: AUTH_E2E_KB, entry_type: 'note', title, body: 'socket scope probe' }
				});
				expect(res.ok(), await res.text()).toBeTruthy();
				return (await res.json()).id;
			}

			// Every live-update frame any of the page's sockets receives. The
			// toast is the user-visible symptom; the frame is the leak itself.
			const frames: string[] = [];
			page.on('websocket', (ws) => {
				if (!new URL(ws.url()).pathname.startsWith('/ws')) return; // Vite's HMR socket
				ws.on('framereceived', (frame) => frames.push(String(frame.payload)));
			});

			await loginAs(page, SEEDED_USER.username, SEEDED_USER.password);
			await expect(page).toHaveURL(/localhost:\d+\/$/);

			// `getByText`, against this file's locator rule: the toast has no
			// role, label or test id, and its text (with the entry id) is the
			// one thing that identifies the event it reports.
			//
			// Positive control: signed in, the socket is live and delivers.
			// Without this the absence asserted below would prove nothing (a
			// socket that never connected shows no toast either). Retried
			// because the socket opens asynchronously after login.
			await expect(async () => {
				const id = await createEntry(`socket-before-logout-${Date.now()}`);
				await expect(page.getByText(`New entry created: ${id}`)).toBeVisible({
					timeout: 2_000
				});
			}).toPass({ timeout: 20_000 });

			await page.getByRole('button', { name: 'Log out' }).click();
			await expect(page).toHaveURL(/\/login$/);

			const leaked = await createEntry(`socket-after-logout-${Date.now()}`);
			// The event window: the positive control saw its toast inside 2 s.
			// Watch for the toast APPEARING during the window -- it dismisses
			// itself after a few seconds, so a check at the end would pass even
			// when it had been shown (as it was, on dev before #336).
			const toasted = await page
				.getByText(`New entry created: ${leaked}`)
				.waitFor({ state: 'visible', timeout: 4_000 })
				.then(
					() => true,
					() => false
				);
			expect(toasted, 'the signed-out page toasted the old scope\'s event').toBe(false);
			expect(
				frames.filter((f) => f.includes(leaked)),
				'a socket still carrying the old scope received the event'
			).toEqual([]);
		} finally {
			await writer.dispose();
		}
	});
});
