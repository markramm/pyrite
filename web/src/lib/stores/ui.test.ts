import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock localStorage before importing the store
const localStorageMock = {
	store: {} as Record<string, string>,
	getItem: vi.fn((key: string) => localStorageMock.store[key] ?? null),
	setItem: vi.fn((key: string, value: string) => { localStorageMock.store[key] = value; }),
	removeItem: vi.fn((key: string) => { delete localStorageMock.store[key]; }),
	clear: vi.fn(() => { localStorageMock.store = {}; })
};
vi.stubGlobal('localStorage', localStorageMock);

// Also stub document.documentElement.classList
const classListMock = {
	toggle: vi.fn()
};
Object.defineProperty(document.documentElement, 'classList', { value: classListMock, writable: true });

describe('UIStore', () => {
	beforeEach(() => {
		localStorageMock.store = {};
		localStorageMock.getItem.mockClear();
		localStorageMock.setItem.mockClear();
		classListMock.toggle.mockClear();
	});

	it('defaults to dark theme', async () => {
		const { uiStore } = await import('./ui.svelte');
		expect(uiStore.theme).toBe('dark');
	});

	it('starts with sidebar open', async () => {
		const { uiStore } = await import('./ui.svelte');
		expect(uiStore.sidebarOpen).toBe(true);
	});

	it('has empty toasts initially', async () => {
		const { uiStore } = await import('./ui.svelte');
		expect(uiStore.toasts).toHaveLength(0);
	});

	it('starts with outline panel closed', async () => {
		const { uiStore } = await import('./ui.svelte');
		expect(uiStore.outlinePanelOpen).toBe(false);
	});

	it('toggles outline panel', async () => {
		const { uiStore } = await import('./ui.svelte');
		expect(uiStore.outlinePanelOpen).toBe(false);
		uiStore.toggleOutlinePanel();
		expect(uiStore.outlinePanelOpen).toBe(true);
		uiStore.toggleOutlinePanel();
		expect(uiStore.outlinePanelOpen).toBe(false);
	});
});
