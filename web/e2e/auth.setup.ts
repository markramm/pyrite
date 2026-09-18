/**
 * Phase two of the auth-enabled world's seed: create the one user.
 *
 * `auth-setup.ts`'s `seedAuthWorld()` runs while `playwright.config.ts` is
 * evaluated and builds everything that is a file on disk. The user is not a
 * file: it is a row in `index.db` whose password column is a bcrypt hash that
 * only `AuthService.register` produces, and there is no CLI command that calls
 * it (`pyrite auth` is GitHub OAuth; there is no `pyrite user`). So the user
 * has to be created against a running backend, which means after `webServer`
 * has started — which is exactly what a Playwright setup project is for.
 *
 * This runs as the `auth-setup` project, which the `chromium-auth` project
 * declares as a dependency, so it completes before any auth spec starts and
 * runs exactly once regardless of worker count.
 *
 * Registering (rather than asserting a user already exists) is what makes the
 * world self-building: `seedAuthWorld()` deletes `index.db` every run, so this
 * registration is always the first one, and the first registered user is
 * always given role `admin` (`AuthService.register`).
 */
import { test as setup, expect } from '@playwright/test';

import { AUTH_BACKEND_URL, SEEDED_USER } from './auth-setup';

setup('register the seeded auth user', async ({ request }) => {
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

	const response = await request.post(`${AUTH_BACKEND_URL}/auth/register`, {
		data: {
			username: SEEDED_USER.username,
			password: SEEDED_USER.password,
			display_name: SEEDED_USER.displayName
		}
	});
	expect(
		response.ok(),
		`registering ${SEEDED_USER.username} failed: ${response.status()} ${await response.text()}`
	).toBeTruthy();

	const user = await response.json();
	expect(user.username).toBe(SEEDED_USER.username);
	// First registration gets admin; if it did not, the data directory was not
	// wiped and this world is carrying state from a previous run.
	expect(user.role, 'the first registered user must be admin — was the world wiped?').toBe(
		'admin'
	);
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
