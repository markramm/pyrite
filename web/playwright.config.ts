import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	testDir: 'e2e',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
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
			// Start the FastAPI backend
			command: 'cd .. && .venv/bin/uvicorn pyrite.server.api:app --host 127.0.0.1 --port 8088',
			url: 'http://127.0.0.1:8088/health',
			reuseExistingServer: !process.env.CI,
			timeout: 15000
		},
		{
			// Start the Vite dev server (proxies /api to backend)
			command: 'npx vite dev --port 5173',
			url: 'http://localhost:5173',
			reuseExistingServer: !process.env.CI,
			timeout: 30000,
			stdout: 'pipe'
		}
	]
});
