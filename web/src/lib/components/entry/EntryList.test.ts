import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';

// Must mock $app/navigation since EntryCard imports it
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

// Use vi.hoisted so the mock object is available when vi.mock factory runs (hoisted)
const mockEntryStore = vi.hoisted(() => ({
	entries: [] as any[],
	loading: false,
	error: null as string | null,
	total: 0,
	limit: 50,
	offset: 0,
	loadList: vi.fn()
}));

vi.mock('$lib/stores/entries.svelte', () => ({
	entryStore: mockEntryStore
}));

import EntryList from './EntryList.svelte';

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

beforeEach(() => {
	mockEntryStore.entries = [];
	mockEntryStore.loading = false;
	mockEntryStore.error = null;
	mockEntryStore.total = 0;
	mockEntryStore.limit = 50;
	mockEntryStore.offset = 0;
});

const sampleEntry = {
	id: 'e1',
	kb_name: 'kb1',
	entry_type: 'note',
	title: 'Test Entry',
	body: 'body text',
	summary: 'A summary',
	tags: ['tag1'],
	participants: [],
	sources: [],
	outlinks: [],
	backlinks: [],
	file_path: '/tmp/test.md'
};

describe('EntryList', () => {
	it('shows "Loading entries..." when loading is true', () => {
		mockEntryStore.loading = true;
		render(EntryList);
		expect(screen.getByText('Loading entries...')).toBeInTheDocument();
	});

	it('shows error message when error is set', () => {
		mockEntryStore.error = 'Network failure';
		render(EntryList);
		expect(screen.getByText('Something went wrong')).toBeInTheDocument();
		expect(screen.getByText('Network failure')).toBeInTheDocument();
	});

	it('shows "No entries found" when entries are empty and not loading or error', () => {
		render(EntryList);
		expect(screen.getByText('No entries found')).toBeInTheDocument();
		expect(screen.getByText('New Entry')).toBeInTheDocument();
	});

	it('shows singular "1 entry" count when total is 1', () => {
		mockEntryStore.total = 1;
		mockEntryStore.entries = [sampleEntry];
		render(EntryList);
		expect(screen.getByText('1 entry')).toBeInTheDocument();
	});

	it('shows plural "3 entries" count when total is 3', () => {
		mockEntryStore.total = 3;
		mockEntryStore.entries = [
			{ ...sampleEntry, id: 'e1' },
			{ ...sampleEntry, id: 'e2', title: 'Second Entry' },
			{ ...sampleEntry, id: 'e3', title: 'Third Entry' }
		];
		render(EntryList);
		expect(screen.getByText('3 entries')).toBeInTheDocument();
	});

	it('renders entry titles via EntryCard', () => {
		mockEntryStore.total = 2;
		mockEntryStore.entries = [
			{ ...sampleEntry, id: 'e1', title: 'Alpha Entry' },
			{ ...sampleEntry, id: 'e2', title: 'Beta Entry' }
		];
		render(EntryList);
		expect(screen.getByText('Alpha Entry')).toBeInTheDocument();
		expect(screen.getByText('Beta Entry')).toBeInTheDocument();
	});

	it('shows pagination when totalPages > 1', () => {
		mockEntryStore.total = 100;
		mockEntryStore.limit = 50;
		mockEntryStore.offset = 0;
		mockEntryStore.entries = [sampleEntry];
		render(EntryList);
		expect(screen.getByText('Page 1 of 2')).toBeInTheDocument();
	});

	it('disables Prev button on page 1', () => {
		mockEntryStore.total = 100;
		mockEntryStore.limit = 50;
		mockEntryStore.offset = 0;
		mockEntryStore.entries = [sampleEntry];
		render(EntryList);
		const prevButton = screen.getByText('Prev');
		expect(prevButton).toBeDisabled();
	});

	it('disables Next button on last page', () => {
		mockEntryStore.total = 100;
		mockEntryStore.limit = 50;
		mockEntryStore.offset = 50;
		mockEntryStore.entries = [sampleEntry];
		render(EntryList);
		const nextButton = screen.getByText('Next');
		expect(nextButton).toBeDisabled();
	});

	it('does not show pagination when there is only one page', () => {
		mockEntryStore.total = 5;
		mockEntryStore.limit = 50;
		mockEntryStore.offset = 0;
		mockEntryStore.entries = [sampleEntry];
		render(EntryList);
		expect(screen.queryByText(/Page/)).not.toBeInTheDocument();
	});
});
