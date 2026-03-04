import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import SplitPaneTestWrapper from './SplitPaneTestWrapper.svelte';

const localStorageMock = {
	store: {} as Record<string, string>,
	getItem: vi.fn((key: string) => localStorageMock.store[key] ?? null),
	setItem: vi.fn((key: string, value: string) => {
		localStorageMock.store[key] = value;
	}),
	removeItem: vi.fn(),
	clear: vi.fn()
};
vi.stubGlobal('localStorage', localStorageMock);

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
	localStorageMock.store = {};
});

describe('SplitPane', () => {
	it('when closed, main content is visible but panel content is not', () => {
		render(SplitPaneTestWrapper, { props: { open: false } });
		expect(screen.getByTestId('main-content')).toBeInTheDocument();
		expect(screen.queryByTestId('panel-content')).not.toBeInTheDocument();
	});

	it('when open, both main and panel content are visible', () => {
		render(SplitPaneTestWrapper, { props: { open: true } });
		expect(screen.getByTestId('main-content')).toBeInTheDocument();
		expect(screen.getByTestId('panel-content')).toBeInTheDocument();
	});

	it('when open, a separator role element exists', () => {
		render(SplitPaneTestWrapper, { props: { open: true } });
		expect(screen.getByRole('separator')).toBeInTheDocument();
	});

	it('separator has aria-orientation="vertical" for position="right"', () => {
		render(SplitPaneTestWrapper, { props: { open: true, position: 'right' } });
		const separator = screen.getByRole('separator');
		expect(separator.getAttribute('aria-orientation')).toBe('vertical');
	});

	it('separator has aria-valuenow reflecting the ratio percentage', () => {
		render(SplitPaneTestWrapper, { props: { open: true } });
		const separator = screen.getByRole('separator');
		// Default ratio is 0.7, so aria-valuenow should be 70
		expect(separator.getAttribute('aria-valuenow')).toBe('70');
	});

	it('separator has aria-valuemin="20" and aria-valuemax="80"', () => {
		render(SplitPaneTestWrapper, { props: { open: true } });
		const separator = screen.getByRole('separator');
		expect(separator.getAttribute('aria-valuemin')).toBe('20');
		expect(separator.getAttribute('aria-valuemax')).toBe('80');
	});

	it('reads saved ratio from localStorage on mount', () => {
		localStorageMock.store['pyrite-split-ratio'] = '0.5';
		render(SplitPaneTestWrapper, { props: { open: true } });
		expect(localStorageMock.getItem).toHaveBeenCalledWith('pyrite-split-ratio');
		const separator = screen.getByRole('separator');
		expect(separator.getAttribute('aria-valuenow')).toBe('50');
	});

	it('invalid localStorage value falls back to default ratio', () => {
		localStorageMock.store['pyrite-split-ratio'] = 'abc';
		render(SplitPaneTestWrapper, { props: { open: true } });
		const separator = screen.getByRole('separator');
		expect(separator.getAttribute('aria-valuenow')).toBe('70');
	});

	it('out-of-range localStorage value (< 0.2) falls back to default ratio', () => {
		localStorageMock.store['pyrite-split-ratio'] = '0.1';
		render(SplitPaneTestWrapper, { props: { open: true } });
		const separator = screen.getByRole('separator');
		expect(separator.getAttribute('aria-valuenow')).toBe('70');
	});

	it('when closed, no separator element exists', () => {
		render(SplitPaneTestWrapper, { props: { open: false } });
		expect(screen.queryByRole('separator')).not.toBeInTheDocument();
	});
});
