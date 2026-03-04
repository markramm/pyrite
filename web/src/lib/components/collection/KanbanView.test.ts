import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

import KanbanView from './KanbanView.svelte';

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

const baseEntry = {
	kb_name: 'kb1',
	body: '',
	summary: '',
	participants: [],
	sources: [],
	outlinks: [],
	backlinks: [],
	file_path: '/tmp/test.md'
};

const entries = [
	{
		...baseEntry,
		id: 'e1',
		title: 'Todo Item',
		entry_type: 'task',
		status: 'todo',
		tags: ['a']
	},
	{
		...baseEntry,
		id: 'e2',
		title: 'Done Item',
		entry_type: 'task',
		status: 'done',
		tags: []
	},
	{
		...baseEntry,
		id: 'e3',
		title: 'Also Todo',
		entry_type: 'note',
		status: 'todo',
		tags: ['b', 'c', 'd']
	}
];

describe('KanbanView', () => {
	it('groups entries into columns by status field', () => {
		render(KanbanView, { props: { entries } });
		expect(screen.getByText('todo')).toBeInTheDocument();
		expect(screen.getByText('done')).toBeInTheDocument();
	});

	it('column headers show correct counts', () => {
		render(KanbanView, { props: { entries } });
		// todo column has 2 entries, done has 1
		expect(screen.getByText('2')).toBeInTheDocument();
		expect(screen.getByText('1')).toBeInTheDocument();
	});

	it('entry titles appear in correct columns', () => {
		render(KanbanView, { props: { entries } });
		expect(screen.getByText('Todo Item')).toBeInTheDocument();
		expect(screen.getByText('Done Item')).toBeInTheDocument();
		expect(screen.getByText('Also Todo')).toBeInTheDocument();
	});

	it('entry type badges are rendered', () => {
		render(KanbanView, { props: { entries } });
		const taskBadges = screen.getAllByText('task');
		expect(taskBadges.length).toBe(2);
		expect(screen.getByText('note')).toBeInTheDocument();
	});

	it('columnOrder controls column display order', () => {
		const { container } = render(KanbanView, {
			props: { entries, columnOrder: ['done', 'todo'] }
		});
		const headers = container.querySelectorAll('h3');
		const headerTexts = Array.from(headers).map((h) => h.textContent?.trim());
		expect(headerTexts[0]).toBe('done');
		expect(headerTexts[1]).toBe('todo');
	});

	it('entries without groupBy field value go to "Ungrouped" column', () => {
		const ungroupedEntry = {
			...baseEntry,
			id: 'e4',
			title: 'No Status',
			entry_type: 'note',
			tags: []
		};
		render(KanbanView, { props: { entries: [ungroupedEntry as never] } });
		expect(screen.getByText('Ungrouped')).toBeInTheDocument();
		expect(screen.getByText('No Status')).toBeInTheDocument();
	});

	it('empty entries array shows "No entries to display" message', () => {
		render(KanbanView, { props: { entries: [] } });
		expect(
			screen.getByText('No entries to display. Try grouping by a different field.')
		).toBeInTheDocument();
	});

	it('column has role="group" with aria-label', () => {
		render(KanbanView, { props: { entries } });
		expect(screen.getByRole('group', { name: 'Kanban column: todo' })).toBeInTheDocument();
		expect(screen.getByRole('group', { name: 'Kanban column: done' })).toBeInTheDocument();
	});

	it('empty column shows "No entries" text', () => {
		render(KanbanView, {
			props: { entries, columnOrder: ['todo', 'done', 'in-review'] }
		});
		expect(screen.getByText('No entries')).toBeInTheDocument();
	});

	it('cards show entry title text', () => {
		render(KanbanView, { props: { entries: [entries[0]] } });
		expect(screen.getByText('Todo Item')).toBeInTheDocument();
	});
});
