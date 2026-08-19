/**
 * Task API client for the Pyrite REST API.
 *
 * Backs the human worklist board (/tasks), which answers one question:
 * what is waiting on a person rather than on an agent?
 */

export interface Task {
	id: string;
	title: string;
	status: string;
	assignee: string;
	priority: number;
	parent: string;
	kb_name: string;
	/** Why the task is parked. Drives the worklist columns. */
	parked_awaiting: string;
	updated_at: string;
}

export interface TaskList {
	count: number;
	tasks: Task[];
}

export interface TaskListParams {
	kb?: string;
	status?: string;
	assignee?: string;
	parent?: string;
}

async function request<T>(path: string): Promise<T> {
	const res = await fetch(path, {
		headers: { 'Content-Type': 'application/json' }
	});
	if (!res.ok) {
		const error = await res.json().catch(() => ({ message: res.statusText }));
		throw new Error(error.detail ?? error.message ?? res.statusText);
	}
	return res.json();
}

export async function listTasks(p: TaskListParams = {}): Promise<TaskList> {
	const params = new URLSearchParams();
	if (p.kb) params.set('kb', p.kb);
	if (p.status) params.set('status', p.status);
	if (p.assignee) params.set('assignee', p.assignee);
	if (p.parent) params.set('parent', p.parent);
	const qs = params.toString();
	return request(`/api/tasks${qs ? `?${qs}` : ''}`);
}

/**
 * The worklist's organising idea: tasks are grouped by what unblocks them,
 * not by status. A browser session takes five minutes; a FOIA takes five
 * minutes and then six weeks of statutory silence. Sorting those together
 * by priority is what buries the five-minute ones.
 */
export type Lane = 'now' | 'send' | 'decide' | 'watching' | 'unsorted';

export const LANES: { id: Lane; label: string; blurb: string; reasons: string[] }[] = [
	{
		id: 'now',
		label: 'Do now',
		blurb: 'Minutes, at a keyboard',
		reasons: ['browser-session']
	},
	{
		id: 'decide',
		label: 'Decide',
		blurb: 'Needs your judgment, nothing else',
		reasons: ['decision']
	},
	{
		id: 'send',
		label: 'Send, then wait',
		blurb: 'Quick to file, slow to return',
		reasons: ['foia-response', 'outreach']
	},
	{
		id: 'watching',
		label: 'Watching',
		blurb: 'The world moves; you don’t',
		reasons: ['external-clock', 'upstream-gate']
	},
	{
		id: 'unsorted',
		label: 'Unsorted',
		blurb: 'No parked_awaiting set — needs a reason',
		reasons: []
	}
];

export function laneFor(task: Task): Lane {
	const r = (task.parked_awaiting || '').toLowerCase();
	if (!r) return 'unsorted';
	for (const lane of LANES) {
		if (lane.reasons.includes(r)) return lane.id;
	}
	// A reason we don't recognise is still a signal — surface it rather than
	// quietly filing it under a lane it may not belong to.
	return 'unsorted';
}

/** Days since the task last moved. The worklist's one piece of pressure. */
export function daysStale(task: Task): number | null {
	if (!task.updated_at) return null;
	const t = Date.parse(task.updated_at);
	if (Number.isNaN(t)) return null;
	return Math.floor((Date.now() - t) / 86_400_000);
}
