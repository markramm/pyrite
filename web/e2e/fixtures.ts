/**
 * The e2e test world: what `global-setup.ts` seeds, as constants specs assert on.
 *
 * This file is the contract between the seed and the specs. Nothing here is
 * read from the running system — these are the literal values `global-setup.ts`
 * writes through the Pyrite CLI, so a spec that asserts on them is asserting on
 * a world that is defined, not on whatever the machine happened to contain.
 *
 * Entry ids are the slug of the title (`pyrite.schema.validators.generate_entry_id`),
 * which is why every seeded title is plain ASCII.
 *
 * See kb/backlog/playwright-e2e-suite-non-deterministic-failures-*.md, Package A.
 */

/** The only KB the e2e backend knows about. */
export const E2E_KB = 'e2e';

/**
 * Auth is explicitly DISABLED for the e2e backend (`auth.enabled: false`, no
 * api_key). `verify_api_key` then resolves every caller to role `admin`, so:
 *
 *   - `/login` and `/register` are not the app's operating mode; auth specs
 *     must either skip or run under their own auth-enabled project (package C);
 *   - every request has write tier, so `GET /daily/{date}` DOES create a note
 *     for a date that has none. The seed therefore pre-creates every date the
 *     specs navigate to (see `SEEDED_DAILY_DATES`), which makes those GETs
 *     reads and leaves the world unchanged by a read-only run.
 */
export const AUTH_ENABLED = false;

export interface SeededEntry {
	/** Entry id = slug of the title. */
	id: string;
	title: string;
	type: string;
}

export const SEEDED_PEOPLE: SeededEntry[] = [
	{ id: 'e2e-person-ada-lovelace', title: 'E2E Person Ada Lovelace', type: 'person' },
	{ id: 'e2e-person-grace-hopper', title: 'E2E Person Grace Hopper', type: 'person' },
	{ id: 'e2e-person-alan-turing', title: 'E2E Person Alan Turing', type: 'person' }
];

/** Events carry a fixed `date`, so timeline ordering is deterministic. */
export const SEEDED_EVENTS: (SeededEntry & { date: string })[] = [
	{ id: 'e2e-event-first-light', title: 'E2E Event First Light', type: 'event', date: '2020-01-15' },
	{
		id: 'e2e-event-second-signal',
		title: 'E2E Event Second Signal',
		type: 'event',
		date: '2021-06-30'
	},
	{ id: 'e2e-event-third-pass', title: 'E2E Event Third Pass', type: 'event', date: '2022-11-02' }
];

export const SEEDED_NOTES: SeededEntry[] = [
	{ id: 'e2e-note-alpha', title: 'E2E Note Alpha', type: 'note' },
	{ id: 'e2e-note-beta', title: 'E2E Note Beta', type: 'note' }
];

export const SEEDED_ORGANIZATIONS: SeededEntry[] = [
	{ id: 'e2e-org-difference-engine-co', title: 'E2E Org Difference Engine Co', type: 'organization' }
];

/** A query collection over the seeded people, so it is never empty. */
export const SEEDED_COLLECTION: SeededEntry & { query: string } = {
	id: 'e2e-collection-people',
	title: 'E2E Collection People',
	type: 'collection',
	query: 'type:person'
};

/**
 * A daily note on a date that never moves — for specs that need a note whose
 * content and date are both known in advance.
 */
export const SEEDED_FIXED_DAILY_DATE = '2020-03-04';

/** `YYYY-MM-DD` in local time, matching what the daily UI computes from `new Date()`. */
export function isoLocalDate(d: Date): string {
	const y = d.getFullYear();
	const m = String(d.getMonth() + 1).padStart(2, '0');
	const day = String(d.getDate()).padStart(2, '0');
	return `${y}-${m}-${day}`;
}

/** `offset` days from today, local time. */
export function dateOffsetFromToday(offset: number): string {
	const d = new Date();
	d.setDate(d.getDate() + offset);
	return isoLocalDate(d);
}

/**
 * Every date the daily specs can land on: today, and the days reachable by the
 * prev/next buttons they click. Seeding all of them keeps `GET /daily/{date}`
 * a read for the whole suite.
 */
export const DAILY_OFFSETS_SEEDED = [-3, -2, -1, 0, 1, 2] as const;

/** Resolved at import time in the same process that runs the specs. */
export const SEEDED_DAILY_DATES: string[] = [
	SEEDED_FIXED_DAILY_DATE,
	...DAILY_OFFSETS_SEEDED.map(dateOffsetFromToday)
];

/** Every non-daily entry the seed creates. */
export const SEEDED_ENTRIES: SeededEntry[] = [
	...SEEDED_PEOPLE,
	...SEEDED_EVENTS,
	...SEEDED_NOTES,
	...SEEDED_ORGANIZATIONS,
	SEEDED_COLLECTION
];

/**
 * A title no other run will produce, for specs that CREATE entries.
 *
 * A spec that writes must never write a title another spec asserts on, and must
 * never collide with itself on a re-run: the seeded world is reset per run, but
 * a writing spec still shares the world with its siblings inside one run.
 */
let uniqueCounter = 0;
export function uniqueTitle(prefix = 'E2E Temp'): string {
	uniqueCounter += 1;
	const stamp = `${Date.now().toString(36)}${uniqueCounter.toString(36)}`;
	// Keep it ASCII and space-separated so the derived id stays predictable.
	return `${prefix} ${stamp}`;
}

/** The entry id Pyrite will derive from a title (mirrors `generate_entry_id`). */
export function idForTitle(title: string): string {
	return title
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '')
		.slice(0, 80)
		.replace(/-+$/g, '');
}
