/**
 * The live-update socket's dev-server proxy entry (#421), shared between
 * `vite.config.ts` (the base world) and `vite.e2e-auth.config.ts` (Package
 * C's auth-enabled world) so the two definitions cannot drift apart the way
 * a copy-pasted literal would.
 *
 * Not `changeOrigin`: the server's `/ws` handshake (`origin_allowed` in
 * `pyrite/server/websocket.py:42-60`) admits an `Origin` that matches its
 * `Host`. The browser's `Origin` is this dev server, so the proxied `Host`
 * forwarded to the backend must stay this dev server too -- `changeOrigin:
 * true` would rewrite `Host` to the backend's own address and the handshake
 * would then refuse it.
 */
export function wsProxy(target: string): Record<string, { target: string; ws: true; changeOrigin: false }> {
	return { '/ws': { target, ws: true, changeOrigin: false } };
}
