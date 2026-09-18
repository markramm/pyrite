import { defineConfig, devices } from '@playwright/test';

import { E2E_ENV, seedE2EWorld } from './e2e/global-setup';

// Build the seeded world NOW, while this config module is evaluated — not from
// Playwright's `globalSetup` hook, which runs after `webServer` has already
// started and the backend has already read its config. See global-setup.ts.
seedE2EWorld();

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
			use: { ...devices['Desktop Chrome'] }
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
		}
	]
});
