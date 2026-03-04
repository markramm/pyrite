import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/svelte';

vi.mock('$lib/api/client', () => ({
	api: {
		getDailyNote: vi.fn(),
		updateEntry: vi.fn()
	}
}));
vi.mock('$lib/stores/kbs.svelte', () => ({
	kbStore: { activeKB: 'test-kb' }
}));
vi.mock('$lib/stores/ui.svelte', () => ({
	uiStore: { toast: vi.fn() }
}));
vi.mock('$lib/editor/Editor.svelte', () => ({
	default: vi.fn()
}));
vi.mock('marked', () => ({
	marked: { parse: vi.fn((md: string) => `<p>${md}</p>`) }
}));

import { api } from '$lib/api/client';
import DailyNote from './DailyNote.svelte';

const mockGetDailyNote = vi.mocked(api.getDailyNote);
const mockUpdateEntry = vi.mocked(api.updateEntry);

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

const sampleEntry = {
	id: 'daily-2026-03-15',
	kb_name: 'test-kb',
	entry_type: 'daily_note',
	title: '2026-03-15',
	body: '# Daily note content',
	tags: [],
	participants: [],
	sources: [],
	outlinks: [],
	backlinks: [],
	file_path: '/tmp/daily.md'
};

describe('DailyNote', () => {
	it('shows "Previous day" button', () => {
		mockGetDailyNote.mockResolvedValue(sampleEntry as never);
		render(DailyNote, {
			props: { selectedDate: '2026-03-15', onnavigate: vi.fn() }
		});
		expect(screen.getByLabelText('Previous day')).toBeInTheDocument();
	});

	it('shows "Next day" button', () => {
		mockGetDailyNote.mockResolvedValue(sampleEntry as never);
		render(DailyNote, {
			props: { selectedDate: '2026-03-15', onnavigate: vi.fn() }
		});
		expect(screen.getByLabelText('Next day')).toBeInTheDocument();
	});

	it('shows "Today" button', () => {
		mockGetDailyNote.mockResolvedValue(sampleEntry as never);
		render(DailyNote, {
			props: { selectedDate: '2026-03-15', onnavigate: vi.fn() }
		});
		expect(screen.getByText('Today')).toBeInTheDocument();
	});

	it('displays formatted date in header', () => {
		mockGetDailyNote.mockResolvedValue(sampleEntry as never);
		render(DailyNote, {
			props: { selectedDate: '2026-03-15', onnavigate: vi.fn() }
		});
		// formatDisplayDate produces a long format including month name
		expect(screen.getByText(/March/)).toBeInTheDocument();
	});

	it('shows "Loading..." when loading', () => {
		// Never resolve so the component stays in loading state
		mockGetDailyNote.mockReturnValue(new Promise(() => {}));
		render(DailyNote, {
			props: { selectedDate: '2026-03-15', onnavigate: vi.fn() }
		});
		expect(screen.getByText('Loading...')).toBeInTheDocument();
	});

	it('clicking prev day calls onnavigate with previous date', async () => {
		mockGetDailyNote.mockResolvedValue(sampleEntry as never);
		const onnavigate = vi.fn();
		render(DailyNote, {
			props: { selectedDate: '2026-03-15', onnavigate }
		});
		await fireEvent.click(screen.getByLabelText('Previous day'));
		expect(onnavigate).toHaveBeenCalledWith('2026-03-14');
	});

	it('clicking next day calls onnavigate with next date', async () => {
		mockGetDailyNote.mockResolvedValue(sampleEntry as never);
		const onnavigate = vi.fn();
		render(DailyNote, {
			props: { selectedDate: '2026-03-15', onnavigate }
		});
		await fireEvent.click(screen.getByLabelText('Next day'));
		expect(onnavigate).toHaveBeenCalledWith('2026-03-16');
	});

	it('year boundary: clicking prev on Jan 1 navigates to Dec 31 of previous year', async () => {
		mockGetDailyNote.mockResolvedValue(sampleEntry as never);
		const onnavigate = vi.fn();
		render(DailyNote, {
			props: { selectedDate: '2026-01-01', onnavigate }
		});
		await fireEvent.click(screen.getByLabelText('Previous day'));
		expect(onnavigate).toHaveBeenCalledWith('2025-12-31');
	});

	it('after loading, shows "Edit" button', async () => {
		mockGetDailyNote.mockResolvedValue(sampleEntry as never);
		render(DailyNote, {
			props: { selectedDate: '2026-03-15', onnavigate: vi.fn() }
		});
		await waitFor(() => {
			expect(screen.getByText('Edit')).toBeInTheDocument();
		});
	});

	it('shows error text when API fails', async () => {
		mockGetDailyNote.mockRejectedValue(new Error('Network error'));
		render(DailyNote, {
			props: { selectedDate: '2026-03-15', onnavigate: vi.fn() }
		});
		await waitFor(() => {
			expect(screen.getByText('Network error')).toBeInTheDocument();
		});
	});

	it('clicking "Today" calls onnavigate with today\'s date', async () => {
		mockGetDailyNote.mockResolvedValue(sampleEntry as never);
		const onnavigate = vi.fn();
		render(DailyNote, {
			props: { selectedDate: '2026-03-15', onnavigate }
		});
		await fireEvent.click(screen.getByText('Today'));
		const now = new Date();
		const y = now.getFullYear();
		const m = String(now.getMonth() + 1).padStart(2, '0');
		const day = String(now.getDate()).padStart(2, '0');
		expect(onnavigate).toHaveBeenCalledWith(`${y}-${m}-${day}`);
	});

	it('loading fetches daily note from API', () => {
		mockGetDailyNote.mockResolvedValue(sampleEntry as never);
		render(DailyNote, {
			props: { selectedDate: '2026-03-15', onnavigate: vi.fn() }
		});
		expect(mockGetDailyNote).toHaveBeenCalledWith('2026-03-15', 'test-kb');
	});
});
