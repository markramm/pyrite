/**
 * Build the deterministic world the e2e suite runs against.
 *
 * `playwright.config.ts` calls `seedE2EWorld()` at module scope, NOT through
 * Playwright's `globalSetup` hook. That is deliberate and load-bearing:
 * Playwright starts `webServer` in a plugin setup task, and plugin setup tasks
 * run BEFORE globalSetup tasks (`runner/tasks.js: createGlobalSetupTasks`).
 * The backend calls `load_config()` once at import, so a globalSetup that
 * wipes and reseeds the data directory would do so after the server had
 * already read an empty one — every entry lookup then 404s. Seeding while the
 * config module is being evaluated happens before any task exists, so the
 * server's first read of the world is a read of the finished world.
 *
 * Everything here is done through the Pyrite CLI against a private data
 * directory; the backend the config then launches points at that directory and
 * sees nothing else.
 *
 * Why this exists: the suite used to start `uvicorn pyrite.server.api:app` with
 * no `PYRITE_*` environment at all. Locally that resolved to the developer's
 * real `~/.pyrite` (dozens of KBs, live daily notes, other sessions writing);
 * on a CI runner it resolved to an empty home with zero KBs. Every spec asserts
 * on data, so the suite was deterministic on its input and its input was
 * undefined — which is what "fails differently every run" actually was.
 *
 * The world it builds is described, entry by entry, in `fixtures.ts`.
 * See kb/backlog/playwright-e2e-suite-non-deterministic-failures-*.md, Package A.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
	E2E_KB,
	SEEDED_COLLECTION,
	SEEDED_DAILY_DATES,
	SEEDED_EVENTS,
	SEEDED_NOTES,
	SEEDED_ORGANIZATIONS,
	SEEDED_PEOPLE
} from './fixtures';

const here = dirname(fileURLToPath(import.meta.url));
/** Repo root: web/e2e -> web -> repo. */
export const REPO_ROOT = resolve(here, '..', '..');
/** The private data directory every e2e process uses instead of ~/.pyrite. */
export const E2E_DATA_DIR = join(REPO_ROOT, 'web', '.e2e-data');
export const E2E_KB_PATH = join(E2E_DATA_DIR, 'kbs', E2E_KB);

const PYRITE_BIN = join(REPO_ROOT, '.venv', 'bin', 'pyrite');

/**
 * The environment every e2e backend process gets. `playwright.config.ts` passes
 * this to the `webServer` command, and the seed below runs under it too, so the
 * CLI that writes the world and the server that reads it agree on where it is.
 *
 * - `PYRITE_DATA_DIR` overrides `~/.pyrite` for config, index and workspace.
 * - `PYRITE_CONFIG_DIR` is the older name for the same thing; set both so the
 *   value does not depend on which one `pyrite.config` happens to check first.
 * - `PYRITE_AUTH_ENABLED=false` makes the auth contract explicit rather than
 *   whatever `load_config()` resolves to. With auth off every caller is
 *   `admin` — see `AUTH_ENABLED` in fixtures.ts for what that means for specs.
 * - `PYRITE_AUTO_EMBED=0` and `HF_HUB_OFFLINE=1` keep the backend from
 *   downloading or loading a sentence-transformers model on first write, which
 *   is both slow and a network dependency a test suite must not have.
 * - `RATELIMIT_ENABLED=false` (slowapi's own switch) turns off the read limiter
 *   for the test backend. Five Playwright workers share one client IP and blow
 *   through `rate_limit_read: 100/minute` partway through a suite, so a page
 *   renders "API Error 429" instead of its content — and WHICH page loses the
 *   race varies run to run. Measured against the seeded backend: 150 reads give
 *   100x200 + 50x429 with the limiter on, and 150x200 with it off. The limiter
 *   is a production behaviour with its own backend tests; it is not what these
 *   specs are asserting.
 */
export const E2E_ENV: Record<string, string> = {
	PYRITE_DATA_DIR: E2E_DATA_DIR,
	PYRITE_CONFIG_DIR: E2E_DATA_DIR,
	PYRITE_AUTH_ENABLED: 'false',
	PYRITE_AUTO_EMBED: '0',
	PYRITE_SEARCH_MODE: 'keyword',
	HF_HUB_OFFLINE: '1',
	TRANSFORMERS_OFFLINE: '1',
	RATELIMIT_ENABLED: 'false'
};

function pyrite(args: string[]): string {
	return execFileSync(PYRITE_BIN, args, {
		cwd: REPO_ROOT,
		env: { ...process.env, ...E2E_ENV },
		encoding: 'utf8',
		stdio: ['ignore', 'pipe', 'pipe']
	});
}

function create(args: string[]): void {
	pyrite(['create', '-k', E2E_KB, ...args]);
}

/**
 * Marker so the seed runs exactly once per `playwright test` invocation.
 *
 * `playwright.config.ts` is evaluated in the main runner process AND again in
 * every worker process, so an unguarded call wipes and rebuilds the data
 * directory N+1 times concurrently — workers racing each other into
 * `rmSync`/`pyrite create` and failing with "Command failed". Observed exactly
 * that: 118 of 119 tests erroring at 0 ms in the seed call.
 *
 * Workers are forked with `{...process.env}` from the main process
 * (`runner/processHost.js`), so a variable set here on the first evaluation is
 * inherited by every worker and seen as already-set.
 */
const SEED_MARKER = 'PYRITE_E2E_SEEDED';

/** Wipe and rebuild the seeded world. Runs once per test invocation. */
export function seedE2EWorld(): void {
	// A worker process never seeds: the main process already did, and the world
	// it built is the one this worker's backend is serving.
	if (process.env[SEED_MARKER] === '1' || process.env.TEST_WORKER_INDEX !== undefined) {
		return;
	}
	process.env[SEED_MARKER] = '1';

	if (!existsSync(PYRITE_BIN)) {
		throw new Error(
			`Pyrite CLI not found at ${PYRITE_BIN}. Create the venv first ` +
				`(pip install -e ".[all,dev]") — the e2e suite seeds its world through the CLI.`
		);
	}

	// A fresh world every run. Without this, a spec that wrote in run N would
	// still be in the world in run N+1, which is the shared-state failure mode
	// this package exists to remove.
	rmSync(E2E_DATA_DIR, { recursive: true, force: true });
	mkdirSync(E2E_DATA_DIR, { recursive: true });

	pyrite(['init', '-t', 'research', '-p', E2E_KB_PATH, '-n', E2E_KB, '--no-examples']);

	for (const p of SEEDED_PEOPLE) {
		create(['-t', 'person', '--title', p.title, '-b', `Seeded person: ${p.title}.`, '--tags', 'e2e,person']);
	}
	for (const e of SEEDED_EVENTS) {
		create([
			'-t', 'event',
			'--title', e.title,
			'-d', e.date,
			'-b', `Seeded event on ${e.date}.`,
			'--tags', 'e2e,event'
		]);
	}
	for (const n of SEEDED_NOTES) {
		create(['-t', 'note', '--title', n.title, '-b', `Seeded note: ${n.title}.`, '--tags', 'e2e,note']);
	}
	for (const o of SEEDED_ORGANIZATIONS) {
		create(['-t', 'organization', '--title', o.title, '-b', `Seeded organization.`, '--tags', 'e2e,org']);
	}

	// `collection` is not one of the `research` template's declared types, so it
	// needs --allow-undeclared; the collections API reads it by `type:` alone.
	create([
		'-t', 'collection',
		'--title', SEEDED_COLLECTION.title,
		'-b', 'Seeded query collection over the seeded people.',
		'-f', 'source_type=query',
		'-f', `query=${SEEDED_COLLECTION.query}`,
		'--tags', 'e2e',
		'--allow-undeclared'
	]);

	// Daily notes. The entry id a daily note must have is `daily-YYYY-MM-DD`, and
	// `pyrite create` derives the id from the title, so the title is chosen to
	// slug to exactly that. The displayed heading comes from the selected date in
	// the UI, not from this title.
	//
	// These are not decoration: with auth disabled every caller is admin, so
	// `GET /daily/{date}` creates a note when none exists. Seeding every date the
	// specs can reach makes each of those GETs a read, and a read-only suite run
	// leaves the world byte-identical.
	for (const date of SEEDED_DAILY_DATES) {
		create([
			'-t', 'note',
			'--title', `daily ${date}`,
			'-b', `# Seeded daily note ${date}\n\nSeeded by the e2e global setup.`,
			'--tags', 'daily,e2e'
		]);
	}

	pyrite(['index', 'sync']);
}

export default seedE2EWorld;
