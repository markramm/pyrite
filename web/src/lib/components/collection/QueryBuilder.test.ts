import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/svelte';

vi.mock('$lib/api/client', () => ({
	api: {
		previewCollectionQuery: vi.fn()
	}
}));

import { api } from '$lib/api/client';
import QueryBuilder from './QueryBuilder.svelte';

const mockPreview = vi.mocked(api.previewCollectionQuery);

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
	vi.restoreAllMocks();
});

const makeMockEntry = (id: string, title: string, type: string = 'note') => ({
	id,
	kb_name: 'test',
	entry_type: type,
	title,
	body: '',
	summary: '',
	tags: [],
	participants: [],
	sources: [],
	outlinks: [],
	backlinks: [],
	file_path: `/tmp/${id}.md`,
	updated_at: '2025-06-15T10:00:00Z'
});

describe('QueryBuilder', () => {
	it('renders the query input with correct placeholder text', () => {
		render(QueryBuilder);
		const input = screen.getByPlaceholderText('e.g. type:backlog_item status:proposed tags:core');
		expect(input).toBeInTheDocument();
	});

	it('shows empty state message initially', () => {
		render(QueryBuilder);
		expect(
			screen.getByText('Enter a query above to preview matching entries.')
		).toBeInTheDocument();
	});

	it('renders all 8 operator chip buttons', () => {
		render(QueryBuilder);
		const labels = ['type:', 'tags:', 'status:', 'date_from:', 'date_to:', 'kb:', 'sort:', 'limit:'];
		for (const label of labels) {
			expect(screen.getByText(label)).toBeInTheDocument();
		}
	});

	it('renders Preview button', () => {
		render(QueryBuilder);
		expect(screen.getByText('Preview')).toBeInTheDocument();
	});

	it('clicking an operator chip appends example to input', async () => {
		vi.useFakeTimers();
		const onQueryChange = vi.fn();
		mockPreview.mockResolvedValue({ entries: [], total: 0, query_parsed: {} });

		render(QueryBuilder, { props: { onQueryChange } });
		const typeChip = screen.getByText('type:');
		await fireEvent.click(typeChip);

		const input = screen.getByPlaceholderText(
			'e.g. type:backlog_item status:proposed tags:core'
		) as HTMLInputElement;
		expect(input.value).toBe('type:note');

		vi.useRealTimers();
	});

	it('clicking operator chip on non-empty query appends with space', async () => {
		vi.useFakeTimers();
		mockPreview.mockResolvedValue({ entries: [], total: 0, query_parsed: {} });

		render(QueryBuilder, { props: { initialQuery: 'status:proposed' } });

		const tagsChip = screen.getByText('tags:');
		await fireEvent.click(tagsChip);

		const input = screen.getByPlaceholderText(
			'e.g. type:backlog_item status:proposed tags:core'
		) as HTMLInputElement;
		expect(input.value).toBe('status:proposed tags:core,api');

		vi.useRealTimers();
	});

	it('clicking Preview button triggers API call', async () => {
		mockPreview.mockResolvedValue({ entries: [], total: 0, query_parsed: {} });

		render(QueryBuilder, { props: { initialQuery: 'type:note' } });
		const previewBtn = screen.getByText('Preview');
		await fireEvent.click(previewBtn);

		await waitFor(() => {
			expect(mockPreview).toHaveBeenCalledWith('type:note', undefined, 10);
		});
	});

	it('preview shows result count text', async () => {
		mockPreview.mockResolvedValue({
			entries: [makeMockEntry('e1', 'Entry One')],
			total: 5,
			query_parsed: {}
		});

		render(QueryBuilder, { props: { initialQuery: 'type:note' } });
		await fireEvent.click(screen.getByText('Preview'));

		await waitFor(() => {
			expect(screen.getByText('5 matching entries')).toBeInTheDocument();
		});
	});

	it('preview shows entry titles', async () => {
		mockPreview.mockResolvedValue({
			entries: [
				makeMockEntry('e1', 'Alpha Entry', 'note'),
				makeMockEntry('e2', 'Beta Entry', 'backlog_item')
			],
			total: 2,
			query_parsed: {}
		});

		render(QueryBuilder, { props: { initialQuery: 'type:note' } });
		await fireEvent.click(screen.getByText('Preview'));

		await waitFor(() => {
			expect(screen.getByText('Alpha Entry')).toBeInTheDocument();
			expect(screen.getByText('Beta Entry')).toBeInTheDocument();
		});
	});

	it('preview shows overflow count', async () => {
		mockPreview.mockResolvedValue({
			entries: [
				makeMockEntry('e1', 'First Entry'),
				makeMockEntry('e2', 'Second Entry')
			],
			total: 15,
			query_parsed: {}
		});

		render(QueryBuilder, { props: { initialQuery: 'type:note' } });
		await fireEvent.click(screen.getByText('Preview'));

		await waitFor(() => {
			expect(screen.getByText('...and 13 more')).toBeInTheDocument();
		});
	});

	it('preview shows parsed query pills', async () => {
		mockPreview.mockResolvedValue({
			entries: [makeMockEntry('e1', 'Test')],
			total: 1,
			query_parsed: { type: 'note' }
		});

		render(QueryBuilder, { props: { initialQuery: 'type:note' } });
		await fireEvent.click(screen.getByText('Preview'));

		await waitFor(() => {
			expect(screen.getByText('type: note')).toBeInTheDocument();
		});
	});

	it('error state shows error message', async () => {
		mockPreview.mockRejectedValue(new Error('Invalid query syntax'));

		render(QueryBuilder, { props: { initialQuery: 'bad:query' } });
		await fireEvent.click(screen.getByText('Preview'));

		await waitFor(() => {
			expect(screen.getByText('Invalid query syntax')).toBeInTheDocument();
		});
	});
});
