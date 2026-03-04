import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';

// Create a reactive mock for uiStore
const mockToasts: Array<{ id: number; message: string; type: string }> = [];

vi.mock('$lib/stores/ui.svelte', () => ({
	uiStore: {
		get toasts() {
			return mockToasts;
		}
	}
}));

import Toast from './Toast.svelte';

afterEach(() => {
	cleanup();
	mockToasts.length = 0;
});

describe('Toast', () => {
	it('renders nothing when no toasts exist', () => {
		const { container } = render(Toast);
		expect(container.querySelector('.fixed')).toBeNull();
	});

	it('renders toast message text when toasts exist', () => {
		mockToasts.push({ id: 1, message: 'Operation successful', type: 'success' });
		render(Toast);
		expect(screen.getByText('Operation successful')).toBeInTheDocument();
	});

	it('success toast has green styling class', () => {
		mockToasts.push({ id: 1, message: 'Saved', type: 'success' });
		render(Toast);
		const toastEl = screen.getByText('Saved').closest('[class*="border-green"]');
		expect(toastEl).not.toBeNull();
	});

	it('error toast has red styling class', () => {
		mockToasts.push({ id: 1, message: 'Failed', type: 'error' });
		render(Toast);
		const toastEl = screen.getByText('Failed').closest('[class*="border-red"]');
		expect(toastEl).not.toBeNull();
	});

	it('info toast has zinc styling class', () => {
		mockToasts.push({ id: 1, message: 'FYI', type: 'info' });
		render(Toast);
		const toastEl = screen.getByText('FYI').closest('[class*="border-zinc"]');
		expect(toastEl).not.toBeNull();
	});

	it('multiple toasts render all messages', () => {
		mockToasts.push(
			{ id: 1, message: 'First toast', type: 'success' },
			{ id: 2, message: 'Second toast', type: 'error' },
			{ id: 3, message: 'Third toast', type: 'info' }
		);
		render(Toast);
		expect(screen.getByText('First toast')).toBeInTheDocument();
		expect(screen.getByText('Second toast')).toBeInTheDocument();
		expect(screen.getByText('Third toast')).toBeInTheDocument();
	});
});
