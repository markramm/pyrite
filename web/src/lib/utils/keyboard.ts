/**
 * Global keyboard shortcut manager.
 *
 * Supports modifier combos (Cmd/Ctrl, Shift, Alt) and prevents conflicts.
 * Automatically maps "mod" to Cmd on Mac and Ctrl elsewhere.
 */

export type Modifier = 'mod' | 'ctrl' | 'shift' | 'alt' | 'meta';

export interface ShortcutOptions {
	key: string;
	modifiers: Modifier[];
	callback: (e: KeyboardEvent) => void;
}

interface RegisteredShortcut extends ShortcutOptions {
	id: string;
}

function shortcutId(key: string, modifiers: Modifier[]): string {
	const sorted = [...modifiers].sort();
	return `${sorted.join('+')}+${key.toLowerCase()}`;
}

const isMac =
	typeof navigator !== 'undefined' ? /Mac|iPhone|iPad|iPod/i.test(navigator.userAgent) : false;

function modifiersMatch(e: KeyboardEvent, modifiers: Modifier[]): boolean {
	const needCtrl = modifiers.includes('ctrl');
	const needMeta = modifiers.includes('meta');
	const needMod = modifiers.includes('mod');
	const needShift = modifiers.includes('shift');
	const needAlt = modifiers.includes('alt');

	const wantCtrl = needCtrl || (needMod && !isMac);
	const wantMeta = needMeta || (needMod && isMac);

	return (
		e.ctrlKey === wantCtrl &&
		e.metaKey === wantMeta &&
		e.shiftKey === needShift &&
		e.altKey === needAlt
	);
}

class KeyboardManager {
	private shortcuts: Map<string, RegisteredShortcut> = new Map();
	private listening = false;
	private handler: ((e: KeyboardEvent) => void) | null = null;

	register(options: ShortcutOptions): string {
		const id = shortcutId(options.key, options.modifiers);
		if (this.shortcuts.has(id)) {
			throw new Error(`Keyboard shortcut conflict: ${id} is already registered`);
		}
		this.shortcuts.set(id, { ...options, id });
		this.ensureListening();
		return id;
	}

	unregister(key: string, modifiers?: Modifier[]): void {
		if (modifiers) {
			const id = shortcutId(key, modifiers);
			this.shortcuts.delete(id);
		} else {
			// Treat as raw id
			this.shortcuts.delete(key);
		}
		if (this.shortcuts.size === 0) {
			this.stopListening();
		}
	}

	unregisterAll(): void {
		this.shortcuts.clear();
		this.stopListening();
	}

	has(key: string, modifiers: Modifier[]): boolean {
		return this.shortcuts.has(shortcutId(key, modifiers));
	}

	private ensureListening(): void {
		if (this.listening || typeof window === 'undefined') return;
		this.handler = (e: KeyboardEvent) => this.handleKeydown(e);
		window.addEventListener('keydown', this.handler);
		this.listening = true;
	}

	private stopListening(): void {
		if (!this.listening || typeof window === 'undefined' || !this.handler) return;
		window.removeEventListener('keydown', this.handler);
		this.handler = null;
		this.listening = false;
	}

	private handleKeydown(e: KeyboardEvent): void {
		for (const shortcut of this.shortcuts.values()) {
			if (
				e.key.toLowerCase() === shortcut.key.toLowerCase() &&
				modifiersMatch(e, shortcut.modifiers)
			) {
				e.preventDefault();
				e.stopPropagation();
				shortcut.callback(e);
				return;
			}
		}
	}
}

export const keyboard = new KeyboardManager();

/**
 * Convenience: register a shortcut and return an unregister function.
 */
export function registerShortcut(
	key: string,
	modifiers: Modifier[],
	callback: (e: KeyboardEvent) => void
): () => void {
	const id = keyboard.register({ key, modifiers, callback });
	return () => keyboard.unregister(id);
}

/**
 * Convenience: unregister by key+modifiers.
 */
export function unregisterShortcut(key: string, modifiers: Modifier[]): void {
	keyboard.unregister(key, modifiers);
}

/**
 * Format a shortcut for display (e.g. "Cmd+K" on Mac, "Ctrl+K" elsewhere).
 */
export function formatShortcut(key: string, modifiers: Modifier[]): string {
	const parts: string[] = [];
	for (const m of modifiers) {
		if (m === 'mod') {
			parts.push(isMac ? '\u2318' : 'Ctrl');
		} else if (m === 'ctrl') {
			parts.push(isMac ? '\u2303' : 'Ctrl');
		} else if (m === 'meta') {
			parts.push(isMac ? '\u2318' : 'Win');
		} else if (m === 'shift') {
			parts.push(isMac ? '\u21E7' : 'Shift');
		} else if (m === 'alt') {
			parts.push(isMac ? '\u2325' : 'Alt');
		}
	}
	parts.push(key.length === 1 ? key.toUpperCase() : key);
	return parts.join(isMac ? '' : '+');
}
