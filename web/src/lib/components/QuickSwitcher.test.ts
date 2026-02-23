import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/svelte';
import QuickSwitcher from './QuickSwitcher.svelte';
import { keyboard } from '$lib/utils/keyboard';

// Mock the API client
vi.mock('$lib/api/client', () => ({
	api: {
		search: vi.fn()
	}
}));

import { api } from '$lib/api/client';

const mockSearch = vi.mocked(api.search);

beforeEach(() => {
	mockSearch.mockReset();
	keyboard.unregisterAll();
});

afterEach(() => {
	cleanup();
});

async function openSwitcher() {
	window.dispatchEvent(
		new KeyboardEvent('keydown', { key: 'o', ctrlKey: true, bubbles: true })
	);
	await waitFor(() => {
		expect(screen.getByTestId('quick-switcher-backdrop')).toBeInTheDocument();
	});
}

describe('QuickSwitcher', () => {
	it('does not render modal by default', () => {
		render(QuickSwitcher);
		expect(screen.queryByTestId('quick-switcher-backdrop')).not.toBeInTheDocument();
	});

	it('opens on Ctrl+O keyboard shortcut', async () => {
		render(QuickSwitcher);
		await openSwitcher();
		expect(screen.getByTestId('quick-switcher-input')).toBeInTheDocument();
	});

	it('closes on Escape', async () => {
		render(QuickSwitcher);
		await openSwitcher();

		const backdrop = screen.getByTestId('quick-switcher-backdrop');
		await fireEvent.keyDown(backdrop, { key: 'Escape' });

		await waitFor(() => {
			expect(screen.queryByTestId('quick-switcher-backdrop')).not.toBeInTheDocument();
		});
	});

	it('searches entries on input with debounce', async () => {
		vi.useFakeTimers();
		mockSearch.mockResolvedValue({
			query: 'test',
			count: 1,
			results: [
				{
					id: 'entry-1',
					kb_name: 'research',
					entry_type: 'note',
					title: 'Test Entry',
					tags: []
				}
			]
		});

		render(QuickSwitcher);
		await openSwitcher();

		const input = screen.getByTestId('quick-switcher-input');
		await fireEvent.input(input, { target: { value: 'test' } });

		// Before debounce, search should not be called
		expect(mockSearch).not.toHaveBeenCalled();

		// Advance past debounce
		await vi.advanceTimersByTimeAsync(350);

		expect(mockSearch).toHaveBeenCalledWith('test', { limit: 20 });
		vi.useRealTimers();
	});

	it('displays search results', async () => {
		mockSearch.mockResolvedValue({
			query: 'test',
			count: 2,
			results: [
				{ id: 'e1', kb_name: 'kb1', entry_type: 'note', title: 'First', tags: [] },
				{ id: 'e2', kb_name: 'kb2', entry_type: 'event', title: 'Second', tags: [] }
			]
		});

		render(QuickSwitcher);
		await openSwitcher();

		const input = screen.getByTestId('quick-switcher-input');
		await fireEvent.input(input, { target: { value: 'test' } });

		// Wait for debounce and results
		await waitFor(() => {
			expect(screen.getByText('First')).toBeInTheDocument();
		}, { timeout: 2000 });

		expect(screen.getByText('Second')).toBeInTheDocument();
		expect(screen.getByText('note')).toBeInTheDocument();
		expect(screen.getByText('event')).toBeInTheDocument();
		expect(screen.getByText('kb1')).toBeInTheDocument();
		expect(screen.getByText('kb2')).toBeInTheDocument();
	});

	it('navigates results with arrow keys', async () => {
		mockSearch.mockResolvedValue({
			query: 'test',
			count: 2,
			results: [
				{ id: 'e1', kb_name: 'kb1', entry_type: 'note', title: 'First', tags: [] },
				{ id: 'e2', kb_name: 'kb2', entry_type: 'event', title: 'Second', tags: [] }
			]
		});

		render(QuickSwitcher);
		await openSwitcher();

		const input = screen.getByTestId('quick-switcher-input');
		await fireEvent.input(input, { target: { value: 'test' } });

		await waitFor(() => {
			expect(screen.getByTestId('quick-switcher-results')).toBeInTheDocument();
		}, { timeout: 2000 });

		const backdrop = screen.getByTestId('quick-switcher-backdrop');

		// First item should be selected
		let items = screen.getAllByTestId('quick-switcher-result');
		expect(items[0].getAttribute('aria-selected')).toBe('true');

		// Arrow down
		await fireEvent.keyDown(backdrop, { key: 'ArrowDown' });
		await waitFor(() => {
			items = screen.getAllByTestId('quick-switcher-result');
			expect(items[1].getAttribute('aria-selected')).toBe('true');
		});
	});

	it('shows empty state when query has no results', async () => {
		mockSearch.mockResolvedValue({
			query: 'zzz',
			count: 0,
			results: []
		});

		render(QuickSwitcher);
		await openSwitcher();

		const input = screen.getByTestId('quick-switcher-input');
		await fireEvent.input(input, { target: { value: 'zzz' } });

		await waitFor(() => {
			expect(screen.getByTestId('quick-switcher-empty')).toBeInTheDocument();
		}, { timeout: 2000 });
	});

	it('registers keyboard shortcut on mount', () => {
		render(QuickSwitcher);
		expect(keyboard.has('o', ['mod'])).toBe(true);
	});
});
