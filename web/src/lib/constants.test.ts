import { describe, it, expect } from 'vitest';
import { typeColor, typeBgColor, typeColors, defaultTypeColor, defaultTypeBgColor } from './constants';

describe('constants', () => {
	it('typeColor returns #3b82f6 for event', () => {
		expect(typeColor('event')).toBe('#3b82f6');
	});

	it('typeColor returns #8b5cf6 for person', () => {
		expect(typeColor('person')).toBe('#8b5cf6');
	});

	it('typeColor returns defaultTypeColor for unknown type', () => {
		expect(typeColor('unknown_type')).toBe(defaultTypeColor);
		expect(typeColor('unknown_type')).toBe('#71717a');
	});

	it('typeBgColor for event contains bg-blue-100', () => {
		expect(typeBgColor('event')).toContain('bg-blue-100');
	});

	it('typeBgColor for unknown type returns defaultTypeBgColor containing bg-zinc-100', () => {
		expect(typeBgColor('unknown_type')).toBe(defaultTypeBgColor);
		expect(typeBgColor('unknown_type')).toContain('bg-zinc-100');
	});

	it('typeColors has at least 20 entries', () => {
		expect(Object.keys(typeColors).length).toBeGreaterThanOrEqual(20);
	});
});
