/**
 * The Vite dev server for the auth-enabled e2e world (Playwright package C).
 *
 * The browser never talks to the backend directly — it fetches `/auth/config`,
 * `/auth/login` and `/api/*` as same-origin paths, which the dev server
 * proxies. That proxy has exactly one target, so a second backend needs a
 * second dev server, and a second dev server needs a config whose proxy points
 * at it.
 *
 * This is a NEW file rather than an edit to `vite.config.ts` on purpose:
 * `vite.config.ts` is what every other e2e spec, `npm run dev`, `npm run
 * build` and the unit tests run under, and four other packages of this fan-out
 * are editing specs against it right now. Extending it by import keeps the
 * single shared definition of the app (plugins, resolve, test) in one place
 * while overriding only the two things this world changes: which port the dev
 * server listens on, and which backend its proxy forwards to.
 *
 * Ports and the reason they are what they are live in `e2e/auth-setup.ts`.
 */
import { mergeConfig, type UserConfig } from 'vite';

import { AUTH_BACKEND_PORT, AUTH_WEB_PORT } from './e2e/auth-setup';
import baseConfig from './vite.config';
import { wsProxy } from './vite.ws-proxy';

/** Every prefix `vite.config.ts` proxies, re-pointed at the auth backend. */
const target = `http://127.0.0.1:${AUTH_BACKEND_PORT}`;
const proxy = Object.fromEntries(
	['/api', '/health', '/auth', '/branding', '/config'].map((prefix) => [
		prefix,
		{ target, changeOrigin: true }
	])
);

export default mergeConfig(baseConfig as UserConfig, {
	server: {
		port: AUTH_WEB_PORT,
		// Fail loudly rather than silently sliding to 5175 if something else
		// holds the port: a dev server on an unexpected port would leave the
		// spec talking to A's world through A's proxy.
		strictPort: true,
		// wsProxy(target) is the same shared entry `vite.config.ts` now also
		// uses for its own /ws (#421) -- one definition of the socket proxy
		// shape, pointed at each world's own backend.
		proxy: { ...proxy, ...wsProxy(target) }
	}
} satisfies UserConfig);
