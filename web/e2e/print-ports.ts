#!/usr/bin/env node
/**
 * Print this worktree's derived e2e ports as shell-sourceable `KEY=value`
 * lines — for `scripts/new-worktree.sh` to record in `.pyrite/e2e-ports` and
 * for a human to `cat` when they want to run `lsof` or `curl` against a
 * specific worktree's servers by hand.
 *
 * Usage: node web/e2e/print-ports.ts <repo-root>
 *
 * Kept separate from `ports.ts` (the pure, tested module) so the CLI framing
 * — argv, stdout — never has to be mocked in the vitest unit tests.
 *
 * Imports `./ports.ts` with the explicit extension: this file runs directly
 * under `node` (scripts/new-worktree.sh, a human's shell), whose native TS
 * support resolves relative imports like plain ESM and needs the extension;
 * Vite/Vitest (which run every other e2e module) resolve extensionless
 * imports themselves, so this is the one file in e2e/ that needs it.
 */
import { derivePorts } from './ports.ts';

const repoRoot = process.argv[2];
if (!repoRoot) {
	console.error('usage: node web/e2e/print-ports.ts <repo-root>');
	process.exit(1);
}

const ports = derivePorts(repoRoot, process.env);

for (const [key, value] of Object.entries({
	PLAYWRIGHT_E2E_PORT: ports.backend,
	PLAYWRIGHT_E2E_VITE_PORT: ports.vite,
	PLAYWRIGHT_E2E_AUTH_PORT: ports.authBackend,
	PLAYWRIGHT_E2E_AUTH_VITE_PORT: ports.authVite
})) {
	console.log(`${key}=${value}`);
}
