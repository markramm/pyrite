import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import ErrorState from './ErrorState.svelte';

afterEach(() => {
	cleanup();
});

describe('ErrorState', () => {
	it('renders "Something went wrong" heading', () => {
		render(ErrorState, { props: { message: 'Test error' } });
		expect(screen.getByText('Something went wrong')).toBeInTheDocument();
	});

	it('displays the error message text', () => {
		render(ErrorState, { props: { message: 'Database connection failed' } });
		expect(screen.getByText('Database connection failed')).toBeInTheDocument();
	});

	it('shows "Try Again" button when onretry is provided', () => {
		const onretry = vi.fn();
		render(ErrorState, { props: { message: 'Error', onretry } });
		expect(screen.getByText('Try Again')).toBeInTheDocument();
	});

	it('does not show "Try Again" button when onretry is not provided', () => {
		render(ErrorState, { props: { message: 'Error' } });
		expect(screen.queryByText('Try Again')).not.toBeInTheDocument();
	});

	it('clicking "Try Again" calls onretry callback', async () => {
		const onretry = vi.fn();
		render(ErrorState, { props: { message: 'Error', onretry } });
		const button = screen.getByText('Try Again');
		await fireEvent.click(button);
		expect(onretry).toHaveBeenCalledOnce();
	});

	it('"Report this issue" link is present with href containing encoded error message', () => {
		render(ErrorState, { props: { message: 'Something broke badly' } });
		const link = screen.getByText('Report this issue');
		expect(link).toBeInTheDocument();
		expect(link.getAttribute('href')).toContain(encodeURIComponent('Something broke badly'));
	});

	it('"Error details" button is present', () => {
		render(ErrorState, { props: { message: 'Error info' } });
		expect(screen.getByText('Error details')).toBeInTheDocument();
	});

	it('clicking "Error details" reveals a pre element with the message', async () => {
		render(ErrorState, { props: { message: 'Detailed error trace' } });
		const detailsButton = screen.getByText('Error details');
		await fireEvent.click(detailsButton);
		const pre = document.querySelector('pre');
		expect(pre).not.toBeNull();
		expect(pre!.textContent).toBe('Detailed error trace');
	});
});
