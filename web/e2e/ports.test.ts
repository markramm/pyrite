/**
 * RED test for Playwright package A.1 (#118): per-worktree ports must be
 * stable, distinct, and overridable — see
 * kb/backlog/playwright-package-a-1-per-worktree-ports-and-data-dir-118.md.
 */
import { describe, expect, it } from 'vitest';

import { derivePorts } from './ports';

describe('derivePorts', () => {
	it('derives four distinct ports in the 20000-29999 range from a worktree path', () => {
		const ports = derivePorts('/Users/markr/pyrite-wt/feature-playwright-a1-ports', {});
		const values = [ports.backend, ports.vite, ports.authBackend, ports.authVite];
		for (const p of values) {
			expect(p).toBeGreaterThanOrEqual(20000);
			expect(p).toBeLessThanOrEqual(29999);
		}
		expect(new Set(values).size).toBe(4);
	});

	it('is stable: the same worktree path always derives the same ports', () => {
		const a = derivePorts('/Users/markr/pyrite-wt/feature-playwright-a1-ports', {});
		const b = derivePorts('/Users/markr/pyrite-wt/feature-playwright-a1-ports', {});
		expect(a).toEqual(b);
	});

	it('is distinct across different worktree paths (no collision for two real paths)', () => {
		const a = derivePorts('/Users/markr/pyrite-wt/feature-playwright-a1-ports', {});
		const b = derivePorts('/Users/markr/pyrite-wt/feature-release-script', {});
		expect(a.backend).not.toBe(b.backend);
		expect(a.vite).not.toBe(b.vite);
	});

	it('honors PLAYWRIGHT_E2E_PORT and PLAYWRIGHT_E2E_VITE_PORT overrides', () => {
		const ports = derivePorts('/Users/markr/pyrite-wt/feature-playwright-a1-ports', {
			PLAYWRIGHT_E2E_PORT: '21000',
			PLAYWRIGHT_E2E_VITE_PORT: '21001'
		});
		expect(ports.backend).toBe(21000);
		expect(ports.vite).toBe(21001);
		// The auth pair still derives (no override defined for it), and must not
		// collide with the overridden base pair.
		expect(ports.authBackend).not.toBe(21000);
		expect(ports.authBackend).not.toBe(21001);
		expect(ports.authVite).not.toBe(21000);
		expect(ports.authVite).not.toBe(21001);
	});

	it('derives a data-dir suffix from the backend port', () => {
		const ports = derivePorts('/Users/markr/pyrite-wt/feature-playwright-a1-ports', {});
		expect(ports.dataDirSuffix).toBe(String(ports.backend));
	});
});
