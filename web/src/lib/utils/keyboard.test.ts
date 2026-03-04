import { describe, it, expect, beforeEach, vi } from 'vitest';
import { keyboard, registerShortcut, unregisterShortcut, formatShortcut } from './keyboard';

beforeEach(() => {
	keyboard.unregisterAll();
});

describe('shortcutId generation (via register/has)', () => {
	it('register with mod modifier is findable via has', () => {
		keyboard.register({ key: 'k', modifiers: ['mod'], callback: () => {} });
		expect(keyboard.has('k', ['mod'])).toBe(true);
	});

	it('modifiers are sorted so order does not matter', () => {
		keyboard.register({ key: 'k', modifiers: ['shift', 'mod'], callback: () => {} });
		expect(keyboard.has('k', ['mod', 'shift'])).toBe(true);
	});

	it('key is case-insensitive', () => {
		keyboard.register({ key: 'K', modifiers: ['mod'], callback: () => {} });
		expect(keyboard.has('k', ['mod'])).toBe(true);
	});
});

describe('register/unregister', () => {
	it('register returns an ID string', () => {
		const id = keyboard.register({ key: 'k', modifiers: ['mod'], callback: () => {} });
		expect(typeof id).toBe('string');
		expect(id.length).toBeGreaterThan(0);
	});

	it('registering the same shortcut twice throws with conflict message', () => {
		keyboard.register({ key: 'k', modifiers: ['mod'], callback: () => {} });
		expect(() => {
			keyboard.register({ key: 'k', modifiers: ['mod'], callback: () => {} });
		}).toThrowError(/conflict/i);
	});

	it('unregister by key+modifiers removes the shortcut', () => {
		keyboard.register({ key: 'k', modifiers: ['mod'], callback: () => {} });
		expect(keyboard.has('k', ['mod'])).toBe(true);
		keyboard.unregister('k', ['mod']);
		expect(keyboard.has('k', ['mod'])).toBe(false);
	});

	it('unregister by raw ID removes the shortcut', () => {
		const id = keyboard.register({ key: 'k', modifiers: ['ctrl'], callback: () => {} });
		expect(keyboard.has('k', ['ctrl'])).toBe(true);
		keyboard.unregister(id);
		expect(keyboard.has('k', ['ctrl'])).toBe(false);
	});

	it('unregisterAll clears everything', () => {
		keyboard.register({ key: 'a', modifiers: ['ctrl'], callback: () => {} });
		keyboard.register({ key: 'b', modifiers: ['shift'], callback: () => {} });
		keyboard.unregisterAll();
		expect(keyboard.has('a', ['ctrl'])).toBe(false);
		expect(keyboard.has('b', ['shift'])).toBe(false);
	});
});

describe('handleKeydown dispatch', () => {
	it('registered callback fires on matching keydown', () => {
		const cb = vi.fn();
		keyboard.register({ key: 'k', modifiers: ['ctrl'], callback: cb });

		const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true });
		window.dispatchEvent(event);

		expect(cb).toHaveBeenCalledOnce();
	});

	it('non-matching key does not fire callback', () => {
		const cb = vi.fn();
		keyboard.register({ key: 'k', modifiers: ['ctrl'], callback: cb });

		const event = new KeyboardEvent('keydown', { key: 'j', ctrlKey: true, bubbles: true });
		window.dispatchEvent(event);

		expect(cb).not.toHaveBeenCalled();
	});

	it('modifier mismatch does not fire callback', () => {
		const cb = vi.fn();
		keyboard.register({ key: 'k', modifiers: ['ctrl'], callback: cb });

		// Only metaKey, not ctrlKey
		const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true, bubbles: true });
		window.dispatchEvent(event);

		expect(cb).not.toHaveBeenCalled();
	});

	it('matching event calls preventDefault and stopPropagation', () => {
		keyboard.register({ key: 'k', modifiers: ['ctrl'], callback: () => {} });

		const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true });
		const pd = vi.spyOn(event, 'preventDefault');
		const sp = vi.spyOn(event, 'stopPropagation');
		window.dispatchEvent(event);

		expect(pd).toHaveBeenCalledOnce();
		expect(sp).toHaveBeenCalledOnce();
	});

	it('dispatches with ctrlKey=true for ctrl modifier', () => {
		const cb = vi.fn();
		keyboard.register({ key: 's', modifiers: ['ctrl'], callback: cb });

		const event = new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true });
		window.dispatchEvent(event);

		expect(cb).toHaveBeenCalledOnce();
	});

	it('dispatches with metaKey=true for meta modifier', () => {
		const cb = vi.fn();
		keyboard.register({ key: 's', modifiers: ['meta'], callback: cb });

		const event = new KeyboardEvent('keydown', { key: 's', metaKey: true, bubbles: true });
		window.dispatchEvent(event);

		expect(cb).toHaveBeenCalledOnce();
	});
});

describe('registerShortcut convenience', () => {
	it('returns an unregister function', () => {
		const unsub = registerShortcut('k', ['ctrl'], () => {});
		expect(typeof unsub).toBe('function');
		expect(keyboard.has('k', ['ctrl'])).toBe(true);
	});

	it('calling the returned function removes the shortcut', () => {
		const unsub = registerShortcut('k', ['ctrl'], () => {});
		expect(keyboard.has('k', ['ctrl'])).toBe(true);
		unsub();
		expect(keyboard.has('k', ['ctrl'])).toBe(false);
	});
});

describe('formatShortcut', () => {
	it('formatShortcut with mod returns a string containing a modifier symbol', () => {
		const result = formatShortcut('k', ['mod']);
		// On any platform it should contain either the Mac Cmd symbol or "Ctrl"
		expect(result.includes('\u2318') || result.includes('Ctrl')).toBe(true);
	});

	it('formatShortcut with shift+mod includes both modifier symbols', () => {
		const result = formatShortcut('k', ['shift', 'mod']);
		// Should contain shift symbol/text AND mod symbol/text
		const hasShift = result.includes('\u21E7') || result.includes('Shift');
		const hasMod = result.includes('\u2318') || result.includes('Ctrl');
		expect(hasShift).toBe(true);
		expect(hasMod).toBe(true);
	});

	it('single-char key is uppercased', () => {
		const result = formatShortcut('k', ['ctrl']);
		expect(result).toContain('K');
	});

	it('multi-char key is kept as-is', () => {
		const result = formatShortcut('Escape', ['ctrl']);
		expect(result).toContain('Escape');
		// Should NOT be fully uppercased
		expect(result).not.toContain('ESCAPE');
	});
});
