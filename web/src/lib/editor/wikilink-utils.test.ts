import { describe, it, expect } from 'vitest';
import { parseWikilinks, renderWikilinks } from './wikilink-utils';

describe('parseWikilinks', () => {
	it('parses simple wikilink', () => {
		const matches = parseWikilinks('See [[john-doe]] for details');
		expect(matches).toHaveLength(1);
		expect(matches[0].target).toBe('john-doe');
		expect(matches[0].display).toBeUndefined();
		expect(matches[0].full).toBe('[[john-doe]]');
	});

	it('parses wikilink with display text', () => {
		const matches = parseWikilinks('See [[john-doe|John Doe]] for details');
		expect(matches).toHaveLength(1);
		expect(matches[0].target).toBe('john-doe');
		expect(matches[0].display).toBe('John Doe');
	});

	it('parses multiple wikilinks', () => {
		const matches = parseWikilinks('[[alpha]] and [[beta|B]] together');
		expect(matches).toHaveLength(2);
		expect(matches[0].target).toBe('alpha');
		expect(matches[1].target).toBe('beta');
		expect(matches[1].display).toBe('B');
	});

	it('returns empty array for no wikilinks', () => {
		expect(parseWikilinks('plain text')).toHaveLength(0);
	});

	it('handles whitespace in targets', () => {
		const matches = parseWikilinks('[[  some target  ]]');
		expect(matches[0].target).toBe('some target');
	});

	it('tracks start and end positions', () => {
		const text = 'before [[link]] after';
		const matches = parseWikilinks(text);
		expect(matches[0].start).toBe(7);
		expect(matches[0].end).toBe(15);
	});
});

describe('renderWikilinks', () => {
	it('renders simple wikilink as anchor', () => {
		const html = renderWikilinks('<p>See [[john-doe]] here</p>');
		expect(html).toContain('href="/entries/john-doe"');
		expect(html).toContain('class="wikilink"');
		expect(html).toContain('data-wikilink="john-doe"');
		expect(html).toContain('>john-doe</a>');
	});

	it('renders wikilink with display text', () => {
		const html = renderWikilinks('<p>See [[john-doe|John Doe]] here</p>');
		expect(html).toContain('href="/entries/john-doe"');
		expect(html).toContain('>John Doe</a>');
	});

	it('encodes special characters in href', () => {
		const html = renderWikilinks('<p>[[entry with spaces]]</p>');
		expect(html).toContain('href="/entries/entry%20with%20spaces"');
	});

	it('leaves text without wikilinks unchanged', () => {
		const html = '<p>No links here</p>';
		expect(renderWikilinks(html)).toBe(html);
	});

	it('handles multiple wikilinks', () => {
		const html = renderWikilinks('<p>[[a]] and [[b|Beta]]</p>');
		expect(html).toContain('>a</a>');
		expect(html).toContain('>Beta</a>');
	});
});
