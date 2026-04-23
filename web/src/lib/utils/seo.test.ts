import { describe, it, expect } from 'vitest';
import type { EntryResponse } from '$lib/api/types';
import { buildEntrySeo, entryDescription, schemaTypeFor } from './seo';

const minimalEntry: EntryResponse = {
	id: 'hello-world',
	kb_name: 'public-kb',
	entry_type: 'note',
	title: 'Hello World',
	summary: 'A first entry.',
	body: 'Some body text.',
	tags: [],
	participants: [],
	sources: [],
	outlinks: [],
	backlinks: [],
	file_path: '/tmp/hello-world.md',
	updated_at: '2026-04-23T12:00:00Z',
	created_at: '2026-04-20T09:00:00Z'
};

const defaultBrand = {
	name: 'Pyrite',
	og_image_url: null,
	site_url: ''
};

const brandedBrand = {
	name: 'Transparency Cascade Press',
	og_image_url: '/branding/og.png',
	site_url: 'https://investigate.example.org'
};

describe('schemaTypeFor', () => {
	it('maps known entry types', () => {
		expect(schemaTypeFor('note')).toBe('Article');
		expect(schemaTypeFor('person')).toBe('Person');
		expect(schemaTypeFor('event')).toBe('Event');
	});

	it('falls back to Article for unknown types', () => {
		expect(schemaTypeFor('whatever')).toBe('Article');
	});
});

describe('entryDescription', () => {
	it('prefers summary over body', () => {
		expect(entryDescription(minimalEntry)).toBe('A first entry.');
	});

	it('falls back to body when summary is absent', () => {
		const e = { ...minimalEntry, summary: undefined, body: 'A body.' };
		expect(entryDescription(e)).toBe('A body.');
	});

	it('truncates long content at word boundaries', () => {
		const e = {
			...minimalEntry,
			summary: undefined,
			body: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. '.repeat(5)
		};
		const d = entryDescription(e, 80);
		expect(d.length).toBeLessThanOrEqual(81); // +1 for the ellipsis
		expect(d.endsWith('…')).toBe(true);
	});

	it('returns empty string when no content', () => {
		const e = { ...minimalEntry, summary: undefined, body: undefined };
		expect(entryDescription(e)).toBe('');
	});
});

describe('buildEntrySeo', () => {
	it('builds a path-only canonical when brand has no site_url', () => {
		const seo = buildEntrySeo({ entry: minimalEntry, brand: defaultBrand });
		expect(seo.canonical).toBe('/entries/hello-world?kb=public-kb');
	});

	it('builds absolute canonical when brand site_url is set', () => {
		const seo = buildEntrySeo({ entry: minimalEntry, brand: brandedBrand });
		expect(seo.canonical).toBe(
			'https://investigate.example.org/entries/hello-world?kb=public-kb'
		);
	});

	it('full title includes brand name', () => {
		const seo = buildEntrySeo({ entry: minimalEntry, brand: brandedBrand });
		expect(seo.title).toBe('Hello World — public-kb | Transparency Cascade Press');
	});

	it('og title omits brand suffix for readability', () => {
		const seo = buildEntrySeo({ entry: minimalEntry, brand: brandedBrand });
		expect(seo.ogTitle).toBe('Hello World — public-kb');
	});

	it('jsonLd publisher reflects brand name', () => {
		const seo = buildEntrySeo({ entry: minimalEntry, brand: brandedBrand });
		expect((seo.jsonLd.publisher as { name: string }).name).toBe(
			'Transparency Cascade Press'
		);
	});

	it('jsonLd includes datePublished and dateModified when available', () => {
		const seo = buildEntrySeo({ entry: minimalEntry, brand: brandedBrand });
		expect(seo.jsonLd.dateModified).toBe('2026-04-23T12:00:00Z');
		expect(seo.jsonLd.datePublished).toBe('2026-04-20T09:00:00Z');
	});

	it('jsonLd @type reflects schema.org mapping', () => {
		const person = { ...minimalEntry, entry_type: 'person' };
		const seo = buildEntrySeo({ entry: person, brand: defaultBrand });
		expect(seo.jsonLd['@type']).toBe('Person');
	});

	it('honors explicit canonicalUrl override', () => {
		const seo = buildEntrySeo({
			entry: minimalEntry,
			brand: brandedBrand,
			canonicalUrl: 'https://custom.example.com/x'
		});
		expect(seo.canonical).toBe('https://custom.example.com/x');
		expect(seo.ogUrl).toBe('https://custom.example.com/x');
	});

	it('og image comes from brand og_image_url', () => {
		const seo = buildEntrySeo({ entry: minimalEntry, brand: brandedBrand });
		expect(seo.ogImage).toBe('/branding/og.png');

		const noImg = buildEntrySeo({ entry: minimalEntry, brand: defaultBrand });
		expect(noImg.ogImage).toBeNull();
	});
});
