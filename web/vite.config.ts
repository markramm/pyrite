import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			'/api': {
				target: 'http://127.0.0.1:8088',
				changeOrigin: true
			},
			'/health': {
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
