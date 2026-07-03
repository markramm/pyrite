import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

declare const process: { env: Record<string, string | undefined> };

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		// Proxy every top-level prefix the backend actually serves (see
		// pyrite/server/api.py's create_app) -- /auth, /branding, and
		// /config were missing here, so any dev-server or e2e request to
		// them 404'd against Vite itself instead of reaching the backend.
		proxy: {
			'/api': {
				target: 'http://127.0.0.1:8088',
				changeOrigin: true
			},
			'/health': {
				target: 'http://127.0.0.1:8088',
				changeOrigin: true
			},
			'/auth': {
				target: 'http://127.0.0.1:8088',
				changeOrigin: true
			},
			'/branding': {
				target: 'http://127.0.0.1:8088',
				changeOrigin: true
			},
			'/config': {
				target: 'http://127.0.0.1:8088',
				changeOrigin: true
			}
		}
	},
	resolve: process.env.VITEST
		? { conditions: ['browser', 'svelte'] }
		: undefined,
	test: {
		environment: 'jsdom',
		include: ['src/**/*.test.ts'],
		setupFiles: ['src/test-setup.ts']
	}
});
