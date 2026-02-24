import { describe, it, expect } from 'vitest';
import { renderCallouts } from './callouts';

// These tests use the actual HTML output from marked.parse() for each callout pattern.
// marked renders `> [!type] Title\n> Body` as:
//   <blockquote>\n<p>[!type] Title\nBody</p>\n</blockquote>\n

describe('renderCallouts', () => {
	it('converts info callout with title and content', () => {
		const html = '<blockquote>\n<p>[!info] Important\nSome content here</p>\n</blockquote>\n';
		const result = renderCallouts(html);
		expect(result).toContain('class="callout callout-info"');
		expect(result).toContain('class="callout-title"');
		expect(result).toContain('Important');
		expect(result).toContain('callout-content');
		expect(result).toContain('Some content here');
	});

	it('converts warning callout', () => {
		const html = '<blockquote>\n<p>[!warning] Be careful\nDanger ahead</p>\n</blockquote>\n';
		const result = renderCallouts(html);
		expect(result).toContain('callout-warning');
		expect(result).toContain('Be careful');
		expect(result).toContain('Danger ahead');
	});

	it('converts tip callout', () => {
		const html = '<blockquote>\n<p>[!tip] Pro tip\nHelpful advice</p>\n</blockquote>\n';
		const result = renderCallouts(html);
		expect(result).toContain('callout-tip');
		expect(result).toContain('Pro tip');
	});

	it('uses capitalized type as default title when no title given', () => {
		// marked renders `> [!note]\n> Content only` as:
		const html = '<blockquote>\n<p>[!note]\nContent only</p>\n</blockquote>\n';
		const result = renderCallouts(html);
		expect(result).toContain('callout-note');
		// With no title text after [!note], the type name is used
		expect(result).toContain('>Note<');
		expect(result).toContain('Content only');
	});

	it('handles all supported callout types', () => {
		const types = [
			'info', 'warning', 'tip', 'note', 'danger', 'quote',
			'example', 'bug', 'question', 'success', 'failure', 'abstract'
		];
		for (const type of types) {
			const html = `<blockquote>\n<p>[!${type}] Title\nBody</p>\n</blockquote>\n`;
			const result = renderCallouts(html);
			expect(result).toContain(`callout-${type}`);
		}
	});

	it('leaves regular blockquotes unchanged', () => {
		const html = '<blockquote>\n<p>Just a regular quote</p>\n</blockquote>\n';
		const result = renderCallouts(html);
		expect(result).toBe(html);
	});

	it('leaves unknown callout types as blockquotes', () => {
		const html = '<blockquote>\n<p>[!unknown] Title\nBody</p>\n</blockquote>\n';
		const result = renderCallouts(html);
		expect(result).toBe(html);
	});

	it('is case-insensitive for type matching', () => {
		const html = '<blockquote>\n<p>[!INFO] Title\nBody</p>\n</blockquote>\n';
		const result = renderCallouts(html);
		expect(result).toContain('callout-info');
	});

	it('handles callout with title only, no body content', () => {
		const html = '<blockquote>\n<p>[!tip] Just a title</p>\n</blockquote>\n';
		const result = renderCallouts(html);
		expect(result).toContain('callout-tip');
		expect(result).toContain('Just a title');
		expect(result).not.toContain('callout-content');
	});

	it('preserves surrounding HTML', () => {
		const html = '<p>Before</p>\n<blockquote>\n<p>[!info] Title\nContent</p>\n</blockquote>\n<p>After</p>';
		const result = renderCallouts(html);
		expect(result).toContain('<p>Before</p>');
		expect(result).toContain('<p>After</p>');
		expect(result).toContain('callout-info');
	});

	it('handles multiple callouts in same document', () => {
		const html =
			'<blockquote>\n<p>[!info] First\nA</p>\n</blockquote>\n' +
			'<blockquote>\n<p>[!warning] Second\nB</p>\n</blockquote>\n';
		const result = renderCallouts(html);
		expect(result).toContain('callout-info');
		expect(result).toContain('callout-warning');
		expect(result).toContain('First');
		expect(result).toContain('Second');
	});

	it('handles multi-paragraph callout content', () => {
		// marked renders multi-paragraph blockquote content as separate <p> tags
		const html = '<blockquote>\n<p>[!tip] Title\nLine 1</p>\n<p>Line 2</p>\n</blockquote>\n';
		const result = renderCallouts(html);
		expect(result).toContain('callout-tip');
		expect(result).toContain('Title');
		expect(result).toContain('Line 1');
		expect(result).toContain('Line 2');
	});
});
