/**
 * The foundation's own test: the world the specs run against is the world
 * `fixtures.ts` describes, and a read-only run does not change it.
 *
 * Everything here talks to the backend directly rather than through the UI —
 * if this file fails, no UI assertion downstream means anything.
 */
import { expect, test } from '@playwright/test';

import {
	AUTH_ENABLED,
	E2E_KB,
	SEEDED_COLLECTION,
	SEEDED_DAILY_DATES,
	SEEDED_ENTRIES,
	SEEDED_EVENTS,
	SEEDED_NOTES,
	SEEDED_ORGANIZATIONS,
	SEEDED_PEOPLE,
	dateOffsetFromToday,
	idForTitle,
	uniqueTitle
} from './fixtures';

const API = 'http://127.0.0.1:8088';

test.describe('seeded e2e world', () => {
	test('the backend sees exactly one KB, and it is the seeded one', async ({ request }) => {
		const res = await request.get(`${API}/api/kbs`);
		expect(res.ok()).toBeTruthy();
		const body = await res.json();
		const names = (body.kbs ?? body).map((k: { name: string }) => k.name);
		expect(names).toEqual([E2E_KB]);
	});

	test('auth is explicitly disabled', async ({ request }) => {
		const res = await request.get(`${API}/auth/config`);
		expect(res.ok()).toBeTruthy();
		const body = await res.json();
		expect(body.enabled).toBe(AUTH_ENABLED);
	});

	test('the read rate limiter is off, so parallel workers do not 429 each other', async ({
		request
	}) => {
		// Five workers share one client IP; with the limiter on they exhaust
		// rate_limit_read (100/minute) partway through the suite and whichever
		// page loses the race renders "API Error 429" instead of its content.
		const codes = await Promise.all(
			Array.from({ length: 120 }, async () => (await request.get(`${API}/api/kbs`)).status())
		);
		expect(codes.filter((c) => c === 429)).toHaveLength(0);
	});

	test('every seeded entry exists with the id fixtures.ts promises', async ({ request }) => {
		for (const entry of SEEDED_ENTRIES) {
			const res = await request.get(`${API}/api/entries/${entry.id}?kb=${E2E_KB}`);
			expect(res.ok(), `${entry.id} should exist`).toBeTruthy();
			const body = await res.json();
			expect(body.title, `title of ${entry.id}`).toBe(entry.title);
			expect(body.entry_type ?? body.type, `type of ${entry.id}`).toBe(entry.type);
		}
	});

	test('the seed has the counts the packages downstream rely on', async () => {
		expect(SEEDED_PEOPLE.length).toBeGreaterThanOrEqual(3);
		expect(SEEDED_EVENTS.length).toBeGreaterThanOrEqual(3);
		expect(SEEDED_NOTES.length).toBeGreaterThanOrEqual(2);
		expect(SEEDED_ORGANIZATIONS.length).toBeGreaterThanOrEqual(1);
	});

	test('every seeded event carries its fixed date', async ({ request }) => {
		for (const e of SEEDED_EVENTS) {
			const res = await request.get(`${API}/api/entries/${e.id}?kb=${E2E_KB}`);
			expect(res.ok()).toBeTruthy();
			const body = await res.json();
			expect(String(body.date ?? '').slice(0, 10), `date of ${e.id}`).toBe(e.date);
		}
	});

	test('the seeded collection is listed by the collections API', async ({ request }) => {
		const res = await request.get(`${API}/api/collections?kb=${E2E_KB}`);
		expect(res.ok()).toBeTruthy();
		const body = await res.json();
		const ids = (body.collections ?? body).map((c: { id: string }) => c.id);
		expect(ids).toContain(SEEDED_COLLECTION.id);
	});

	test('a daily GET for a seeded date is a read, not a create', async ({ request }) => {
		// Auth is disabled, so the caller is admin and GET /daily/{date} WILL
		// create a note for a date that has none. Every date the specs can reach
		// is seeded precisely so that path is never taken.
		const before = await request.get(`${API}/api/daily/dates?kb=${E2E_KB}`);
		expect(before.ok()).toBeTruthy();
		const datesBefore: string[] = (await before.json()).dates;

		for (const offset of [-1, 0, 1]) {
			const date = dateOffsetFromToday(offset);
			const res = await request.get(`${API}/api/daily/${date}?kb=${E2E_KB}`);
			expect(res.ok(), `daily GET for ${date}`).toBeTruthy();
			expect((await res.json()).id).toBe(`daily-${date}`);
		}

		const after = await request.get(`${API}/api/daily/dates?kb=${E2E_KB}`);
		const datesAfter: string[] = (await after.json()).dates;
		expect(datesAfter.sort()).toEqual(datesBefore.sort());
	});

	test('every date the daily specs can reach is already seeded', async ({ request }) => {
		for (const date of SEEDED_DAILY_DATES) {
			const res = await request.get(`${API}/api/entries/daily-${date}?kb=${E2E_KB}`);
			expect(res.ok(), `daily-${date} should be seeded`).toBeTruthy();
		}
	});

	test('uniqueTitle gives a fresh, slug-safe title every call', async () => {
		const a = uniqueTitle();
		const b = uniqueTitle();
		expect(a).not.toBe(b);
		for (const t of [a, b]) {
			expect(idForTitle(t)).toMatch(/^[a-z0-9][a-z0-9-]{0,79}$/);
		}
	});
});
