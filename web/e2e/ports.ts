/**
 * Per-worktree ports and data-dir suffix for the e2e suite (#118, Package A.1).
 *
 * Package A gave the e2e suite a deterministic world, but the world's PORTS
 * were still hardcoded: 8088/5173 for the base backend/Vite pair, 8189/5274
 * for Package C's auth-enabled pair. Two worktrees running `playwright test`
 * at once collided on those four numbers — Vite's dev server silently slides
 * to the next free port when its own is taken (defeated separately by
 * `strictPort: true` in `vite.config.ts` and `vite.e2e-auth.config.ts`), and
 * uvicorn on a taken port either refuses to start or, worse, a stale process
 * from a *different* worktree answers the health check and the whole run
 * proceeds against a sibling's world.
 *
 * This module derives all four ports from the worktree's own filesystem path,
 * so a worktree gets the same four ports on every run (stable — no config
 * drift between a human's manual run and CI) and a different worktree gets a
 * different four (distinct — the reason two can run at once). `PLAYWRIGHT_E2E_PORT`
 * and `PLAYWRIGHT_E2E_VITE_PORT` override the base pair for a caller (a human,
 * or `scripts/new-worktree.sh` recording a fixed choice) that wants an exact,
 * memorable number instead of a hash.
 */
import { createHash } from 'node:crypto';

export interface E2EPorts {
	/** The base world's backend (uvicorn) port. Was hardcoded 8088. */
	backend: number;
	/** The base world's Vite dev server port. Was hardcoded 5173. */
	vite: number;
	/** Package C's auth-enabled backend port. Was hardcoded 8189. */
	authBackend: number;
	/** Package C's auth-enabled Vite dev server port. Was hardcoded 5274. */
	authVite: number;
	/**
	 * Suffix for this worktree's private data directories, so
	 * `web/.e2e-data-<suffix>` and `web/.e2e-auth-data-<suffix>` never collide
	 * with a sibling worktree's. Derived from the backend port: it is already
	 * unique per worktree and makes the directory name self-explanatory (which
	 * run's data this is) when several show up in `ls`.
	 */
	dataDirSuffix: string;
}

/** The range every derived port falls into (acceptance criterion #1). */
const RANGE_START = 20000;
const RANGE_SIZE = 10000;

/**
 * A stable, non-cryptographic hash of `path` mapped into a sub-range of
 * [RANGE_START, RANGE_START + RANGE_SIZE). `slot` and `slotCount` carve the
 * full range into disjoint bands (one per derived port) so the four ports for
 * one worktree cannot collide with each other by construction, only with
 * another worktree's — and a same-path collision is impossible since the
 * hash is deterministic and each port lives in its own band.
 */
function hashPortInBand(path: string, slot: number, slotCount: number): number {
	const digest = createHash('sha256').update(path).digest();
	// 4 bytes is plenty of entropy for a 10000-wide range and keeps the maths
	// in safe-integer territory without needing bigint.
	const n = digest.readUInt32BE(slot * 4);
	const bandSize = Math.floor(RANGE_SIZE / slotCount);
	const bandStart = RANGE_START + slot * bandSize;
	return bandStart + (n % bandSize);
}

/**
 * Parse a port override, rejecting anything that is not a usable TCP port
 * rather than letting it flow through as `NaN`. An unguarded `Number(...)` on
 * a typo'd or empty override (`PLAYWRIGHT_E2E_PORT=808A`, or a shell that
 * exported the variable name with no value) previously produced `NaN`
 * everywhere it was used — `uvicorn --port NaN` failing opaquely, and
 * `web/.e2e-data-NaN` silently becoming the actual, repeatedly-wiped data
 * directory two different broken worktrees could even share by accident.
 */
function parsePortOverride(varName: string, raw: string): number {
	const n = Number(raw);
	if (!Number.isInteger(n) || n < 1024 || n > 65535) {
		throw new Error(
			`${varName}=${JSON.stringify(raw)} is not a valid TCP port (expected an integer 1024-65535).`
		);
	}
	return n;
}

/**
 * Derive this worktree's four e2e ports and data-dir suffix.
 *
 * @param worktreePath Absolute path identifying the worktree (its repo root).
 *   Two worktrees at different paths derive different ports; the same
 *   worktree always derives the same ones.
 * @param env The environment to read overrides from — pass `process.env` in
 *   real use. A parameter (not a direct `process.env` read) so this stays a
 *   pure function the tests above can exercise without env leakage between
 *   cases.
 */
export function derivePorts(
	worktreePath: string,
	env: Record<string, string | undefined>
): E2EPorts {
	const backend = env.PLAYWRIGHT_E2E_PORT
		? parsePortOverride('PLAYWRIGHT_E2E_PORT', env.PLAYWRIGHT_E2E_PORT)
		: hashPortInBand(worktreePath, 0, 4);
	const vite = env.PLAYWRIGHT_E2E_VITE_PORT
		? parsePortOverride('PLAYWRIGHT_E2E_VITE_PORT', env.PLAYWRIGHT_E2E_VITE_PORT)
		: hashPortInBand(worktreePath, 1, 4);
	// The auth pair has no override of its own: nothing outside this module
	// depends on a fixed auth port, and deriving it from bands 2/3 keeps it
	// clear of the base pair even when the base pair was overridden to a
	// value a hash could have landed on too.
	const authBackend = hashPortInBand(worktreePath, 2, 4);
	const authVite = hashPortInBand(worktreePath, 3, 4);

	return {
		backend,
		vite,
		authBackend,
		authVite,
		dataDirSuffix: String(backend)
	};
}

export default derivePorts;
