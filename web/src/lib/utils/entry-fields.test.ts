import { describe, it, expect } from 'vitest';
import { coerceFieldValue, buildMetadata } from './entry-fields';
import type { TypeFieldSchema } from '$lib/api/types';

const f = (type: string, extra: Partial<TypeFieldSchema> = {}): TypeFieldSchema => ({
	type,
	...extra
});

describe('coerceFieldValue', () => {
	it('coerces number fields to a number', () => {
		expect(coerceFieldValue('42', f('number'))).toBe(42);
		expect(coerceFieldValue('3.5', f('number'))).toBe(3.5);
	});

	it('returns 0 for non-numeric number input', () => {
		expect(coerceFieldValue('abc', f('number'))).toBe(0);
	});

	it('splits list fields on commas, trimming and dropping blanks', () => {
		expect(coerceFieldValue('a, b ,, c', f('list'))).toEqual(['a', 'b', 'c']);
	});

	it('coerces checkbox "true" to boolean true and anything else to false', () => {
		expect(coerceFieldValue('true', f('checkbox'))).toBe(true);
		expect(coerceFieldValue('false', f('checkbox'))).toBe(false);
		// Critically NOT the literal 'on' that a raw checkbox .value yields.
		expect(coerceFieldValue('on', f('checkbox'))).toBe(false);
	});

	it('passes string fields through unchanged', () => {
		expect(coerceFieldValue('hello', f('string'))).toBe('hello');
	});
});

describe('buildMetadata', () => {
	const schema = {
		count: f('number'),
		aliases: f('list'),
		verified: f('checkbox'),
		note: f('string')
	};

	it('includes only non-empty fields, coerced by type', () => {
		const meta = buildMetadata(
			{ count: '7', aliases: 'x, y', verified: 'true', note: '  ' },
			schema
		);
		expect(meta).toEqual({ count: 7, aliases: ['x', 'y'], verified: true });
		expect('note' in meta).toBe(false); // blank dropped
	});

	it('lets a checkbox set to "true" survive even though it is not a number', () => {
		const meta = buildMetadata({ verified: 'true' }, schema);
		expect(meta.verified).toBe(true);
	});

	it('omits a checkbox left at "false"', () => {
		// 'false' is a non-empty string, so it is recorded — as boolean false.
		const meta = buildMetadata({ verified: 'false' }, schema);
		expect(meta.verified).toBe(false);
	});

	it('returns an empty object when nothing is filled', () => {
		expect(buildMetadata({ count: '', aliases: '', note: '' }, schema)).toEqual({});
	});
});
