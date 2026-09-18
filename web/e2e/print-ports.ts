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
 *
 * Passes `{}`, not `process.env`, as `derivePorts`'s override source. This
 * file's only job is to record THIS worktree's derived ports; if the caller's
 * shell happened to have `PLAYWRIGHT_E2E_PORT` set (e.g. exported from a
 * DIFFERENT worktree's `.pyrite/e2e-ports` still sourced in this shell),
 * `process.env` would record that worktree's base pair mixed with this one's
 * derived auth pair — a file named after and meant to represent one
 * worktree, containing a hybrid of two. `playwright.config.ts` itself still
 * reads `process.env` (a real override there is the caller's deliberate
 * choice for THIS run); this script's only purpose is the unconditional
 * derivation.
 */
import { derivePorts } from './ports.ts';

const repoRoot = process.argv[2];
if (!repoRoot) {
	console.error('usage: node web/e2e/print-ports.ts <repo-root>');
	process.exit(1);
}

const ports = derivePorts(repoRoot, {});

// PLAYWRIGHT_E2E_PORT / PLAYWRIGHT_E2E_VITE_PORT are real overrides
// `derivePorts` reads from the environment (see ports.ts) — printing them
// here documents the base pair a human could export to pin it. The two
// PLAYWRIGHT_E2E_AUTH_* lines below are NOT read as overrides by anything;
// they are informational only (there is no override for the auth pair, by
// design — see ports.ts), so they are named accordingly rather than as
// PLAYWRIGHT_E2E_*_PORT env-var lookalikes nothing consumes.
console.log(`PLAYWRIGHT_E2E_PORT=${ports.backend}`);
console.log(`PLAYWRIGHT_E2E_VITE_PORT=${ports.vite}`);
console.log(`# informational only — not read as an override by anything:`);
console.log(`DERIVED_E2E_AUTH_BACKEND_PORT=${ports.authBackend}`);
console.log(`DERIVED_E2E_AUTH_VITE_PORT=${ports.authVite}`);
