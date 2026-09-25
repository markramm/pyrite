/**
 * Check the auth-enabled world's seeded user against the running backend.
 *
 * `auth-setup.ts`'s `seedAuthWorld()` creates the user with
 * `pyrite-admin user create --role admin` while `playwright.config.ts` is
 * evaluated, before `webServer` starts (registration is closed until an admin
 * exists). This setup project confirms, once, that the
 * backend sees that user as an admin who can sign in, so a broken seed fails
 * here with one clear message instead of in every spec.
 *
 * Runs as the `auth-setup` project, which the `chromium-auth` project declares
 * as a dependency.
 */
import { test as setup, expect } from '@playwright/test';

import { AUTH_BACKEND_URL, SEEDED_USER } from './auth-setup';

setup('the seeded admin can sign in', async ({ request }) => {
	// Talk to the backend directly rather than through the dev-server proxy:
	// this is world construction, not a user journey, and it must not depend on
	// the Vite server being up yet.
	const config = await request.get(`${AUTH_BACKEND_URL}/auth/config`);
	expect(config.ok()).toBeTruthy();
	const configBody = await config.json();
	// If this is false the whole project is meaningless — the specs would be
	// asserting on the auth-disabled contract under a second port. Fail here,
	// once, with a clear message, rather than in every spec.
	expect(configBody.enabled, 'the auth-enabled backend must report auth enabled').toBe(true);
	expect(
		configBody.allow_registration,
		'the auth-enabled backend must allow registration'
	).toBe(true);

	const response = await request.post(`${AUTH_BACKEND_URL}/auth/login`, {
		data: { username: SEEDED_USER.username, password: SEEDED_USER.password }
	});
	expect(
		response.ok(),
		`signing in as ${SEEDED_USER.username} failed: ${response.status()} ${await response.text()}`
	).toBeTruthy();

	const user = await response.json();
	expect(user.username).toBe(SEEDED_USER.username);
	expect(user.role, 'the seeded user must be admin — did the CLI seed run?').toBe('admin');
});

/**
 * Pay the dev server's cold-compile cost once, here, instead of in whichever
 * spec happens to hit `/login` first.
 *
 * Vite compiles a route on its first request. The auth project's own dev
 * server has never served anything when the first spec runs, so that spec's
 * `page.goto('/login')` waits for the whole app to build — observed taking
 * over 30 s (the default test timeout) on a machine also running another
 * worktree's suite, failing a test whose assertions were fine. Warming both
 * auth routes in the setup project puts the cost somewhere it is expected,
 * and a setup step is allowed to be slow.
 */
setup('warm the auth dev server', async ({ page }) => {
	// Generous: this is the compile itself, not a behaviour under test.
	setup.setTimeout(180_000);
	await page.goto('/login', { waitUntil: 'load', timeout: 120_000 });
	await page.goto('/register', { waitUntil: 'load', timeout: 120_000 });
});
