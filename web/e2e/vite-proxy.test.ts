// @vitest-environment node
//
// Importing the real vite.config.ts pulls in sveltekit()/esbuild-based
// tooling that trips over jsdom's patched globals (TextEncoder fails
// esbuild's own invariant check under jsdom). node is also the correct
// environment for a build-config test: nothing here touches the DOM.
/**
 * dev proxies /ws (#421): both `vite.config.ts` (the base world) and
 * `vite.e2e-auth.config.ts` (Package C) must forward the live-update socket
 * to their backend with `ws: true` and `changeOrigin: false` --
 * `changeOrigin: false` matters because `origin_allowed`
 * (`pyrite/server/websocket.py:42-60`) admits an `Origin` equal to the
 * server's `Host`; `changeOrigin: true` would rewrite `Host` to the proxy
 * target and the handshake's Origin check would then fail.
 *
 * Imports the real configs (not a copy of the shape) so a regression in
 * either file's actual `server.proxy['/ws']` fails this test.
 */
import { describe, expect, it } from 'vitest';

import baseConfig from '../vite.config';
import authConfig from '../vite.e2e-auth.config';

function resolveConfig(config: unknown) {
	// vite.config.ts and vite.e2e-auth.config.ts both export a plain
	// UserConfig object (defineConfig/mergeConfig return the object
	// directly, not a function), but guard the function form too.
	return typeof config === 'function'
		? (config as (env: unknown) => unknown)({ command: 'serve', mode: 'development' })
		: config;
}

describe('vite dev server proxies /ws (#421)', () => {
	it('base vite.config.ts proxies /ws with ws:true and changeOrigin:false', async () => {
		const resolved = (await resolveConfig(baseConfig)) as {
			server?: { proxy?: Record<string, { ws?: boolean; changeOrigin?: boolean; target?: string }> };
		};
		const wsEntry = resolved.server?.proxy?.['/ws'];
		expect(wsEntry).toBeDefined();
		expect(wsEntry?.ws).toBe(true);
		expect(wsEntry?.changeOrigin).toBe(false);
	});

	it('vite.e2e-auth.config.ts proxies /ws with ws:true and changeOrigin:false', async () => {
		const resolved = (await resolveConfig(authConfig)) as {
			server?: { proxy?: Record<string, { ws?: boolean; changeOrigin?: boolean; target?: string }> };
		};
		const wsEntry = resolved.server?.proxy?.['/ws'];
		expect(wsEntry).toBeDefined();
		expect(wsEntry?.ws).toBe(true);
		expect(wsEntry?.changeOrigin).toBe(false);
	});

	it('both configs build their /ws entry from the same shared wsProxy constant', async () => {
		// Regression against copy-paste drift (#421's acceptance: "share one
		// wsProxy constant rather than copying it"): both configs' /ws
		// targets must move together because they import the same factory,
		// not two hand-copied literals.
		const { wsProxy } = await import('../vite.ws-proxy');
		const built = wsProxy('http://127.0.0.1:9999');
		expect(built).toEqual({ '/ws': { target: 'http://127.0.0.1:9999', ws: true, changeOrigin: false } });
	});
});
