/** Page-level coverage for the Web Clipper (#392, round-1 cold read).
 *
 * Pins the page's own wiring: no preselected declared type, submit disabled
 * before schemas load or after they fail (with a retry, not a silent `note`
 * clip), and a stale getTypeSchemas response for a KB the user has since
 * navigated away from is discarded (the #367/#443 pattern).
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

const mockKBStore = vi.hoisted(() => ({
	activeKB: null as string | null,
	kbs: [
		{ name: 'sw', type: 'software', path: '/tmp/sw', entries: 0, indexed: true },
		{ name: 'plain', type: 'generic', path: '/tmp/plain', entries: 0, indexed: true }
	]
}));
vi.mock('$lib/stores/kbs.svelte', () => ({ kbStore: mockKBStore }));

const mockApi = vi.hoisted(() => ({
	getTypeSchemas: vi.fn(),
	clipUrl: vi.fn()
}));
const MockApiError = vi.hoisted(() => {
	return class MockApiError extends Error {
		status: number;
		detail: string;
		constructor(status: number, detail: string) {
			super(`API Error ${status}: ${detail}`);
			this.status = status;
			this.detail = detail;
		}
	};
});
vi.mock('$lib/api/client', () => ({ api: mockApi, ApiError: MockApiError }));

import ClipPage from './+page.svelte';

const declaredSchemas = {
	adr: { description: '', fields: {} },
	backlog_item: { description: '', fields: {} },
	note: { description: '', fields: {} }
};
const declared = ['adr', 'backlog_item'];

beforeEach(() => {
	vi.clearAllMocks();
	mockKBStore.activeKB = null;
});

afterEach(() => {
	cleanup();
});

async function fillUrlAndKb(kbName: string) {
	await fireEvent.input(screen.getByPlaceholderText('https://example.com/article'), {
		target: { value: 'https://example.org/a' }
	});
	await fireEvent.change(screen.getByLabelText('Knowledge Base'), { target: { value: kbName } });
}

describe('Clip page (#392 round 1)', () => {
	it('does not preselect an arbitrary declared type, and blocks submit until one is chosen', async () => {
		mockApi.getTypeSchemas.mockResolvedValue({ types: declaredSchemas, declared });
		render(ClipPage);
		await fillUrlAndKb('sw');

		await waitFor(() => expect(screen.getByTestId('entry-type-select')).toBeInTheDocument());
		const select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		expect(select.value).toBe('');

		const submit = screen.getByText('Clip Page').closest('button') as HTMLButtonElement;
		expect(submit.disabled).toBe(true);

		await fireEvent.change(select, { target: { value: 'adr' } });
		expect(submit.disabled).toBe(false);
	});

	it('disables submit while type schemas are loading, and does not clip a silent default', async () => {
		let resolveSchemas: (v: unknown) => void = () => {};
		mockApi.getTypeSchemas.mockReturnValue(
			new Promise((resolve) => {
				resolveSchemas = resolve;
			})
		);
		render(ClipPage);
		await fillUrlAndKb('sw');

		const submit = screen.getByText('Clip Page').closest('button') as HTMLButtonElement;
		expect(submit.disabled).toBe(true);

		resolveSchemas({ types: declaredSchemas, declared });
		await waitFor(() => expect(screen.getByTestId('entry-type-select')).toBeInTheDocument());
	});

	it('shows a retry control on a load failure instead of falling back to note', async () => {
		mockApi.getTypeSchemas.mockRejectedValue(new Error('network down'));
		render(ClipPage);
		await fillUrlAndKb('sw');

		await waitFor(() => expect(screen.getByTestId('type-schemas-error')).toBeInTheDocument());
		expect(screen.queryByTestId('entry-type-select')).not.toBeInTheDocument();
		const submit = screen.getByText('Clip Page').closest('button') as HTMLButtonElement;
		expect(submit.disabled).toBe(true);

		mockApi.getTypeSchemas.mockResolvedValue({ types: declaredSchemas, declared });
		await fireEvent.click(screen.getByTestId('type-schemas-retry'));
		await waitFor(() => expect(screen.getByTestId('entry-type-select')).toBeInTheDocument());
	});

	it('discards a stale schemas response for a KB the user has since switched away from', async () => {
		let resolveSw: (v: unknown) => void = () => {};
		mockApi.getTypeSchemas.mockImplementation((kb: string) => {
			if (kb === 'sw') {
				return new Promise((resolve) => {
					resolveSw = resolve;
				});
			}
			return Promise.resolve({
				types: { note: { description: '', fields: {} } },
				declared: []
			});
		});

		render(ClipPage);
		await fillUrlAndKb('sw'); // starts the slow 'sw' request, unresolved
		await fillUrlAndKb('plain'); // switches KB before 'sw' resolves; 'plain' resolves fast (declares none)

		await waitFor(() => expect(screen.getByTestId('entry-type-select')).toBeInTheDocument());
		// 'plain' declares nothing, so its own resolution offers every type,
		// including note, with no declared-type restriction.
		let select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		const plainOptionValues = Array.from(select.options).map((o) => o.value);
		expect(plainOptionValues).toContain('note');

		// Now let the stale 'sw' response land -- it must be discarded, not
		// overwrite 'plain's declared (empty) with sw's (['adr','backlog_item']).
		// A guarded page never applies it, so there is no moment to wait for;
		// settle one macrotask (everything the promise resolution can drive)
		// and assert directly -- waitFor would keep re-checking after a
		// transient pass and could mask a later, wrong, settled state.
		resolveSw({ types: declaredSchemas, declared });
		await new Promise((r) => setTimeout(r, 10));

		select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		const finalValues = Array.from(select.options).map((o) => o.value);
		expect(finalValues).toContain('note');
	});

	it('sends entry_type with no allow_undeclared for a declared choice', async () => {
		mockApi.getTypeSchemas.mockResolvedValue({ types: declaredSchemas, declared });
		mockApi.clipUrl.mockResolvedValue({ created: true, id: 'c1', kb_name: 'sw', title: 't', source_url: 'u' });
		render(ClipPage);
		await fillUrlAndKb('sw');

		await waitFor(() => expect(screen.getByTestId('entry-type-select')).toBeInTheDocument());
		await fireEvent.change(screen.getByTestId('entry-type-select'), { target: { value: 'adr' } });

		const submit = screen.getByText('Clip Page').closest('button') as HTMLButtonElement;
		await fireEvent.click(submit);

		await waitFor(() => expect(mockApi.clipUrl).toHaveBeenCalled());
		const sent = mockApi.clipUrl.mock.calls[0][0];
		expect(sent.entry_type).toBe('adr');
		expect(sent.allow_undeclared).toBeUndefined();
	});
});
