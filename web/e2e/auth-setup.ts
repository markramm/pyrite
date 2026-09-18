/**
 * Build the SECOND e2e world: the one where auth is actually on.
 *
 * Package A's world (`global-setup.ts`) runs with `PYRITE_AUTH_ENABLED=false`
 * so that every other spec has write tier without a session. That makes those
 * specs deterministic, but it also means `/login` in that world is a form
 * nothing is behind: `POST /auth/login` returns 400 "Authentication is not
 * enabled", the root layout's gate never fires, and a spec asserting on the
 * login page there is asserting on dead markup. This file builds a parallel,
 * fully separate world where `auth.enabled` is true, one user exists, and the
 * login path is the path a real deployment uses.
 *
 * Deliberately parallel to `global-setup.ts`, and deliberately NOT a
 * modification of it — A's four files are the contract the other nine specs
 * share, and a second world must not be able to perturb the first.
 *
 * Three constraints inherited from A, all load-bearing:
 *
 * 1. **Seeding happens while `playwright.config.ts` is evaluated**, not in
 *    `globalSetup`. The backend calls `load_config()` once at import, and
 *    Playwright starts `webServer` in a plugin setup task, which runs BEFORE
 *    globalSetup tasks. A globalSetup that wiped and rebuilt the data
 *    directory would do it after the server had read an empty one. See the
 *    header of `global-setup.ts` for the full reasoning; `seedAuthWorld()` is
 *    called from the same module scope for the same reason.
 * 2. **A separate `PYRITE_DATA_DIR`** (`web/.e2e-auth-data`, beside A's
 *    `web/.e2e-data`). Both projects' backends run at once under one
 *    `playwright test`; sharing a data directory would have each wiping the
 *    other's world mid-run. The user record lives in that directory's
 *    `index.db`, so a separate directory is also what keeps the auth-enabled
 *    user out of the auth-disabled world.
 * 3. **Its own port** (8089, beside A's 8088) and its own Vite dev server
 *    (5174, beside A's 5173), because the browser reaches the backend through
 *    Vite's proxy and that proxy has one target. `web/vite.e2e-auth.config.ts`
 *    supplies the second target without touching the shared `vite.config.ts`.
 *
 * The seeded user is created through the REST API rather than the CLI: there
 * is no `pyrite user` command (checked — `pyrite auth` is GitHub OAuth only),
 * and `AuthService.register` is the only code path that produces the bcrypt
 * hash the login endpoint verifies against. That means this seed has two
 * phases: the KB/entries phase runs at config-module scope like A's, and the
 * user phase has to run once the backend is up, which is what
 * `auth.setup.ts` (a Playwright setup project) does.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, rmSync } from 'node:fs';
import { join } from 'node:path';

import { REPO_ROOT } from './global-setup';

/** The auth-enabled world's private data directory — never A's. */
export const AUTH_E2E_DATA_DIR = join(REPO_ROOT, 'web', '.e2e-auth-data');

/** The only KB the auth-enabled backend knows about. */
export const AUTH_E2E_KB = 'e2e-auth';

export const AUTH_E2E_KB_PATH = join(AUTH_E2E_DATA_DIR, 'kbs', AUTH_E2E_KB);

/**
 * The auth-enabled backend's port. A's is 8088.
 *
 * Uvicorn binds the port it is given or exits, so unlike the dev server this
 * one cannot wander onto a neighbour's port; 8189 is simply kept clear of 8088
 * so the two worlds' logs and `lsof` output stay easy to tell apart.
 */
export const AUTH_BACKEND_PORT = 8189;

/**
 * The auth-enabled Vite dev server's port.
 *
 * NOT 5174, deliberately. The shared `vite.config.ts` does not set
 * `strictPort`, so A's dev server — launched as `vite dev --port 5173` — falls
 * through to 5174, then 5175, whenever 5173 is already taken. That happens
 * routinely: several worktrees of this fan-out run the suite at once, and a
 * run killed mid-flight leaves 5173 held for a while. When it happens, A's
 * server lands on this world's port, and this project either fails to start or
 * (worse, without `strictPort` here) silently drives the auth-DISABLED app.
 * 5274 is well clear of that fallthrough range.
 *
 * The real fix is `strictPort: true` in the shared `vite.config.ts` so a
 * misplaced dev server fails loudly instead of migrating — that file is
 * outside this package's footprint, so it is reported rather than changed.
 */
export const AUTH_WEB_PORT = 5274;

export const AUTH_BASE_URL = `http://localhost:${AUTH_WEB_PORT}`;
export const AUTH_BACKEND_URL = `http://127.0.0.1:${AUTH_BACKEND_PORT}`;

/**
 * The user `auth.setup.ts` registers and `auth.spec.ts` logs in as.
 *
 * The first user to register gets role `admin`
 * (`AuthService.register`), which is what makes the post-login app shell
 * render the same surface the auth-disabled world's specs see.
 */
export const SEEDED_USER = {
	username: 'e2e-auth-user',
	password: 'e2e-password-123',
	displayName: 'E2E Auth User'
} as const;

/** A username that is NOT registered, for the invalid-credentials assertion. */
export const UNKNOWN_USER = {
	username: 'e2e-nobody',
	password: 'e2e-not-a-password'
} as const;

/**
 * The environment the auth-enabled backend process gets.
 *
 * Mirrors A's `E2E_ENV` except for the three things this world exists to
 * change: its own data directory, `PYRITE_AUTH_ENABLED=true`, and
 * registration explicitly on (the spec asserts on the register link, which the
 * login page renders only when `allow_registration` is true — an assertion
 * that must not depend on the config default). The offline/embedding/rate-limit
 * settings are copied for the same reasons A documents: no network, no model
 * download, and no 429 from several workers sharing one client IP.
 */
export const AUTH_E2E_ENV: Record<string, string> = {
	PYRITE_DATA_DIR: AUTH_E2E_DATA_DIR,
	PYRITE_CONFIG_DIR: AUTH_E2E_DATA_DIR,
	PYRITE_AUTH_ENABLED: 'true',
	PYRITE_AUTH_ALLOW_REGISTRATION: 'true',
	PYRITE_AUTO_EMBED: '0',
	PYRITE_SEARCH_MODE: 'keyword',
	HF_HUB_OFFLINE: '1',
	TRANSFORMERS_OFFLINE: '1',
	RATELIMIT_ENABLED: 'false'
};

const PYRITE_BIN = join(REPO_ROOT, '.venv', 'bin', 'pyrite');

/**
 * Marker so the seed runs exactly once per `playwright test` invocation.
 *
 * Same mechanism and same reason as A's `PYRITE_E2E_SEEDED`: the config module
 * is evaluated in the main runner process and again in every worker process,
 * and workers inherit `process.env` from the main process. A distinct marker
 * name so the two seeds cannot suppress each other.
 */
const SEED_MARKER = 'PYRITE_E2E_AUTH_SEEDED';

/**
 * Wipe and rebuild the auth-enabled world's data directory and KB.
 *
 * Only the KB: the user cannot be created here, because creating it requires
 * `AuthService` to hash the password, and the only supported way in is
 * `POST /auth/register` against a running backend. `auth.setup.ts` does that
 * part once the backend this seed prepared has started.
 */
export function seedAuthWorld(): void {
	if (process.env[SEED_MARKER] === '1' || process.env.TEST_WORKER_INDEX !== undefined) {
		return;
	}
	process.env[SEED_MARKER] = '1';

	if (!existsSync(PYRITE_BIN)) {
		throw new Error(
			`Pyrite CLI not found at ${PYRITE_BIN}. Create the venv first ` +
				`(pip install -e ".[all,dev]") — the e2e suite seeds its worlds through the CLI.`
		);
	}

	// A fresh world every run, including a fresh index.db — which is where the
	// user table lives, so this is also what guarantees `auth.setup.ts`'s
	// register call is the FIRST registration (and therefore gets admin) on
	// every run rather than only the first.
	rmSync(AUTH_E2E_DATA_DIR, { recursive: true, force: true });
	mkdirSync(AUTH_E2E_DATA_DIR, { recursive: true });

	execFileSync(
		PYRITE_BIN,
		['init', '-t', 'research', '-p', AUTH_E2E_KB_PATH, '-n', AUTH_E2E_KB, '--no-examples'],
		{
			cwd: REPO_ROOT,
			env: { ...process.env, ...AUTH_E2E_ENV },
			encoding: 'utf8',
			stdio: ['ignore', 'pipe', 'pipe']
		}
	);
}

export default seedAuthWorld;
