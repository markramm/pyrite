/**
 * Property-style tests for Playwright package A.1 (#118): per-worktree ports
 * must be stable, distinct, banded, and overridable — see
 * kb/backlog/done/playwright-package-a-1-per-worktree-ports-and-data-dir-118.md.
 *
 * These assert the MECHANISM, not one literal path: a single fixed-path test
 * passes even if the banding is deleted entirely (four ports could still land
 * distinctly by luck on one path) or if the auth pair is hardcoded instead of
 * derived (a fixed path's "derived" auth ports and the hardcoded ones can
 * coincide, or the test simply never notices they're constants). Looping over
 * many generated paths and checking band membership closes both gaps: a
 * flat/undifferentiated port space fails band membership on some path in the
 * loop, and hardcoded auth ports fail band membership as soon as a path's
 * hash does not land there by chance, and fail distinct-per-path lookup since
 * they never change.
 */
import { describe, expect, it } from 'vitest';

import { derivePorts } from './ports';

const RANGE_START = 20000;
const RANGE_SIZE = 10000;
const BAND_SIZE = RANGE_SIZE / 4; // 2500

/** [start, end] inclusive-exclusive band bounds for each of the four ports. */
const BANDS = {
	backend: [RANGE_START + 0 * BAND_SIZE, RANGE_START + 1 * BAND_SIZE], // 20000-22499
	vite: [RANGE_START + 1 * BAND_SIZE, RANGE_START + 2 * BAND_SIZE], // 22500-24999
	authBackend: [RANGE_START + 2 * BAND_SIZE, RANGE_START + 3 * BAND_SIZE], // 25000-27499
	authVite: [RANGE_START + 3 * BAND_SIZE, RANGE_START + 4 * BAND_SIZE] // 27500-29999
} as const;

/** A generous spread of plausible and adversarial worktree paths. */
function generatePaths(n: number): string[] {
	const paths: string[] = [];
	for (let i = 0; i < n; i++) {
		paths.push(`/Users/markr/pyrite-wt/generated-worktree-${i}`);
	}
	// A few real-shaped paths and edge cases, not just the synthetic sequence.
	paths.push(
		'/Users/markr/pyrite-wt/feature-playwright-a1-ports',
		'/Users/markr/pyrite-wt/feature-release-script',
		'/Users/markr/pyrite',
		'/home/ci/runner/work/pyrite/pyrite',
		'',
		'/'
	);
	return paths;
}

const PATHS = generatePaths(300);

describe('derivePorts', () => {
	it('places every derived port in its own disjoint band, for every generated path', () => {
		for (const path of PATHS) {
			const ports = derivePorts(path, {});
			for (const [key, [start, end]] of Object.entries(BANDS) as [
				keyof typeof BANDS,
				[number, number]
			][]) {
				const value = ports[key];
				expect(value, `${key} for ${JSON.stringify(path)}`).toBeGreaterThanOrEqual(start);
				expect(value, `${key} for ${JSON.stringify(path)}`).toBeLessThan(end);
			}
		}
	});

	it('derives four mutually distinct ports, for every generated path', () => {
		for (const path of PATHS) {
			const ports = derivePorts(path, {});
			const values = [ports.backend, ports.vite, ports.authBackend, ports.authVite];
			expect(new Set(values).size, `distinct ports for ${JSON.stringify(path)}`).toBe(4);
		}
	});

	it('is stable: the same worktree path always derives the same ports', () => {
		for (const path of PATHS) {
			const a = derivePorts(path, {});
			const b = derivePorts(path, {});
			expect(a, `stability for ${JSON.stringify(path)}`).toEqual(b);
		}
	});

	it('derives a different auth pair across different paths (auth ports are not hardcoded)', () => {
		// If authBackend/authVite were hardcoded constants, every path would
		// derive the identical pair. Across 300+ generated paths that would
		// collapse this set to size 1.
		const authPairs = new Set(PATHS.map((p) => JSON.stringify([derivePorts(p, {}).authBackend, derivePorts(p, {}).authVite])));
		expect(authPairs.size).toBeGreaterThan(1);
	});

	it('honors PLAYWRIGHT_E2E_PORT and PLAYWRIGHT_E2E_VITE_PORT overrides, and the auth pair still bands correctly', () => {
		for (const path of PATHS.slice(0, 20)) {
			const ports = derivePorts(path, {
				PLAYWRIGHT_E2E_PORT: '21000',
				PLAYWRIGHT_E2E_VITE_PORT: '23000'
			});
			expect(ports.backend).toBe(21000);
			expect(ports.vite).toBe(23000);
			expect(ports.authBackend).toBeGreaterThanOrEqual(BANDS.authBackend[0]);
			expect(ports.authBackend).toBeLessThan(BANDS.authBackend[1]);
			expect(ports.authVite).toBeGreaterThanOrEqual(BANDS.authVite[0]);
			expect(ports.authVite).toBeLessThan(BANDS.authVite[1]);
		}
	});

	it('derives a data-dir suffix from the backend port, for every generated path', () => {
		for (const path of PATHS) {
			const ports = derivePorts(path, {});
			expect(ports.dataDirSuffix).toBe(String(ports.backend));
		}
	});

	it('rejects a non-numeric PLAYWRIGHT_E2E_PORT override rather than deriving NaN', () => {
		expect(() =>
			derivePorts('/Users/markr/pyrite-wt/feature-playwright-a1-ports', {
				PLAYWRIGHT_E2E_PORT: 'not-a-number'
			})
		).toThrow(/PLAYWRIGHT_E2E_PORT/);
	});

	it('rejects a non-numeric PLAYWRIGHT_E2E_VITE_PORT override rather than deriving NaN', () => {
		expect(() =>
			derivePorts('/Users/markr/pyrite-wt/feature-playwright-a1-ports', {
				PLAYWRIGHT_E2E_VITE_PORT: 'not-a-number'
			})
		).toThrow(/PLAYWRIGHT_E2E_VITE_PORT/);
	});

	it('rejects an out-of-range PLAYWRIGHT_E2E_PORT override', () => {
		expect(() =>
			derivePorts('/Users/markr/pyrite-wt/feature-playwright-a1-ports', {
				PLAYWRIGHT_E2E_PORT: '70000'
			})
		).toThrow(/PLAYWRIGHT_E2E_PORT/);
	});
});
