import { defineConfig, devices } from '@playwright/test';

import {
	AUTH_BACKEND_PORT,
	AUTH_BASE_URL,
	AUTH_E2E_ENV,
	AUTH_WEB_PORT,
	seedAuthWorld
} from './e2e/auth-setup';
import { E2E_ENV, seedE2EWorld } from './e2e/global-setup';

// Build the seeded world NOW, while this config module is evaluated — not from
// Playwright's `globalSetup` hook, which runs after `webServer` has already
// started and the backend has already read its config. See global-setup.ts.
seedE2EWorld();

// Package C's second world: the same timing, for the same reason, for a
// backend with `auth.enabled: true`. Its own data directory, port and dev
// server — see e2e/auth-setup.ts for why each of those is separate.
seedAuthWorld();

/**
 * The specs that belong to the auth-enabled world, named once so that the
 * `chromium` project excludes exactly what the `chromium-auth` project
 * includes. Without the exclusion, `auth.spec.ts` would also run against the
 * auth-disabled backend, where every one of its assertions is false.
 */
const AUTH_SPECS = ['**/auth.spec.ts', '**/auth.setup.ts'];

export default defineConfig({
	testDir: 'e2e',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	// A flake must be visible, not absorbed. Retries hid the fact that the suite
	// had no test-data contract; they only made the job three times slower.
	retries: 0,
	workers: process.env.CI ? 1 : undefined,
	reporter: 'list',
	use: {
		baseURL: 'http://localhost:5173',
		trace: 'on-first-retry'
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] },
			// Everything except the auth-enabled world's specs. Added by Package
			// C; the project's `use` and name are untouched.
			testIgnore: AUTH_SPECS
		},
		// --- Package C: the auth-enabled world ---------------------------------
		{
			// Creates the one user, once, against the auth backend. A separate
			// project rather than a `globalSetup` because it must run AFTER
			// `webServer` (the user is created over HTTP), which globalSetup does
			// not — see e2e/auth.setup.ts.
			name: 'auth-setup',
			testMatch: /auth\.setup\.ts/,
			use: { ...devices['Desktop Chrome'], baseURL: AUTH_BASE_URL }
		},
		{
			name: 'chromium-auth',
			testMatch: /auth\.spec\.ts/,
			dependencies: ['auth-setup'],
			// Its own baseURL: the auth-enabled dev server on 5174, whose proxy
			// points at the auth-enabled backend on 8089. A spec in this project
			// that said `page.goto('/login')` against 5173 would be looking at the
			// auth-DISABLED world's login page.
			use: { ...devices['Desktop Chrome'], baseURL: AUTH_BASE_URL }
		}
	],
	webServer: [
		{
			// The FastAPI backend, pointed at the seeded world and nothing else.
			command: 'cd .. && .venv/bin/uvicorn pyrite.server.api:app --host 127.0.0.1 --port 8088',
			url: 'http://127.0.0.1:8088/health',
			env: E2E_ENV,
			// Never reuse: a backend already running on 8088 is somebody's real
			// Pyrite, with their real KBs, and this suite writes.
			reuseExistingServer: false,
			// A cold import of the server stack takes well over 15 s on a loaded
			// or first-run machine.
			timeout: 60000
		},
		{
			// The Vite dev server (proxies /api, /auth, /config, /health to the backend).
			command: 'npx vite dev --port 5173',
			url: 'http://localhost:5173',
			reuseExistingServer: false,
			timeout: 60000,
			stdout: 'pipe'
		},
		// --- Package C: the auth-enabled world's two servers --------------------
		{
			// The same FastAPI app, on its own port, pointed at its own data
			// directory, with `PYRITE_AUTH_ENABLED=true`.
			command: `cd .. && .venv/bin/uvicorn pyrite.server.api:app --host 127.0.0.1 --port ${AUTH_BACKEND_PORT}`,
			url: `http://127.0.0.1:${AUTH_BACKEND_PORT}/health`,
			env: AUTH_E2E_ENV,
			// Same rule as 8088, and the same reason: a backend already on this
			// port is somebody's real Pyrite.
			reuseExistingServer: false,
			timeout: 60000
		},
		{
			// The second Vite dev server, whose only difference from the first is
			// which backend it proxies to. See vite.e2e-auth.config.ts.
			command: `npx vite dev --config vite.e2e-auth.config.ts --port ${AUTH_WEB_PORT}`,
			url: AUTH_BASE_URL,
			reuseExistingServer: false,
			timeout: 60000,
			stdout: 'pipe'
		}
	]
});
