import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/svelte';
import CommandPalette from './CommandPalette.svelte';
import { keyboard } from '$lib/utils/keyboard';

// Mock the UI store
vi.mock('$lib/stores/ui.svelte', () => {
	return {
		uiStore: {
			toggleTheme: vi.fn(),
			theme: 'dark'
		}
	};
});

import { uiStore } from '$lib/stores/ui.svelte';

beforeEach(() => {
	keyboard.unregisterAll();
	vi.mocked(uiStore.toggleTheme).mockReset();
});

afterEach(() => {
	cleanup();
});

async function openPalette() {
	window.dispatchEvent(
		new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true })
	);
	await waitFor(() => {
		expect(screen.getByTestId('command-palette-backdrop')).toBeInTheDocument();
	});
}

describe('CommandPalette', () => {
	it('does not render modal by default', () => {
		render(CommandPalette);
		expect(screen.queryByTestId('command-palette-backdrop')).not.toBeInTheDocument();
	});

	it('opens on Ctrl+K keyboard shortcut', async () => {
		render(CommandPalette);
		await openPalette();
		expect(screen.getByTestId('command-palette-input')).toBeInTheDocument();
	});

	it('shows built-in actions when opened', async () => {
		render(CommandPalette);
		await openPalette();

		expect(screen.getByText('New Entry')).toBeInTheDocument();
		expect(screen.getByText('Search Entries')).toBeInTheDocument();
		expect(screen.getByText('Toggle Theme')).toBeInTheDocument();
	});

	it('filters actions with fuzzy matching', async () => {
		render(CommandPalette);
		await openPalette();

		const input = screen.getByTestId('command-palette-input');
		await fireEvent.input(input, { target: { value: 'theme' } });

		await waitFor(() => {
			expect(screen.getByText('Toggle Theme')).toBeInTheDocument();
			expect(screen.queryByText('New Entry')).not.toBeInTheDocument();
		});
	});

	it('executes action on Enter', async () => {
		render(CommandPalette);
		await openPalette();

		// Filter to Toggle Theme
		const input = screen.getByTestId('command-palette-input');
		await fireEvent.input(input, { target: { value: 'theme' } });

		await waitFor(() => {
			expect(screen.getByText('Toggle Theme')).toBeInTheDocument();
		});

		// Press Enter
		const backdrop = screen.getByTestId('command-palette-backdrop');
		await fireEvent.keyDown(backdrop, { key: 'Enter' });

		expect(uiStore.toggleTheme).toHaveBeenCalled();
	});

	it('closes on Escape', async () => {
		render(CommandPalette);
		await openPalette();

		const backdrop = screen.getByTestId('command-palette-backdrop');
		await fireEvent.keyDown(backdrop, { key: 'Escape' });

		await waitFor(() => {
			expect(screen.queryByTestId('command-palette-backdrop')).not.toBeInTheDocument();
		});
	});

	it('navigates with arrow keys', async () => {
		render(CommandPalette);
		await openPalette();

		const items = screen.getAllByTestId('command-palette-action');
		expect(items[0].getAttribute('aria-selected')).toBe('true');

		const backdrop = screen.getByTestId('command-palette-backdrop');
		await fireEvent.keyDown(backdrop, { key: 'ArrowDown' });

		await waitFor(() => {
			const updatedItems = screen.getAllByTestId('command-palette-action');
			expect(updatedItems[1].getAttribute('aria-selected')).toBe('true');
		});
	});

	it('shows empty state for non-matching query', async () => {
		render(CommandPalette);
		await openPalette();

		const input = screen.getByTestId('command-palette-input');
		await fireEvent.input(input, { target: { value: 'xyznonexistent' } });

		await waitFor(() => {
			expect(screen.getByTestId('command-palette-empty')).toBeInTheDocument();
		});
	});

	it('registers keyboard shortcut on mount', () => {
		render(CommandPalette);
		expect(keyboard.has('k', ['mod'])).toBe(true);
	});
});
