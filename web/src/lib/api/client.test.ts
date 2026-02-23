import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api, ApiError } from './client';

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function jsonResponse(data: unknown, status = 200) {
	return {
		ok: status >= 200 && status < 300,
		status,
		statusText: status === 200 ? 'OK' : 'Error',
		json: () => Promise.resolve(data)
	};
}

beforeEach(() => {
	mockFetch.mockReset();
});

describe('ApiClient', () => {
	describe('listKBs', () => {
		it('fetches /api/kbs and returns typed response', async () => {
			const payload = { kbs: [{ name: 'test', type: 'generic', path: '/tmp', entries: 5, indexed: true }], total: 1 };
			mockFetch.mockResolvedValueOnce(jsonResponse(payload));

			const result = await api.listKBs();
			expect(result.kbs).toHaveLength(1);
			expect(result.kbs[0].name).toBe('test');
			expect(mockFetch).toHaveBeenCalledWith('/api/kbs', expect.objectContaining({ headers: expect.any(Object) }));
		});
	});

	describe('search', () => {
		it('passes query params correctly', async () => {
			mockFetch.mockResolvedValueOnce(jsonResponse({ query: 'test', count: 0, results: [] }));

			await api.search('test', { kb: 'my-kb', limit: 10 });
			const url = mockFetch.mock.calls[0][0] as string;
			expect(url).toContain('q=test');
			expect(url).toContain('kb=my-kb');
			expect(url).toContain('limit=10');
		});
	});

	describe('listEntries', () => {
		it('builds query string from options', async () => {
			mockFetch.mockResolvedValueOnce(jsonResponse({ entries: [], total: 0, limit: 50, offset: 0 }));

			await api.listEntries({ kb: 'events', entry_type: 'note', limit: 20 });
			const url = mockFetch.mock.calls[0][0] as string;
			expect(url).toContain('/api/entries');
			expect(url).toContain('kb=events');
			expect(url).toContain('entry_type=note');
			expect(url).toContain('limit=20');
		});
	});

	describe('getEntry', () => {
		it('encodes entry ID in URL', async () => {
			const entry = { id: 'test-entry', kb_name: 'kb', entry_type: 'note', title: 'Test', tags: [], participants: [], sources: [], outlinks: [], backlinks: [], file_path: '/tmp/test.md' };
			mockFetch.mockResolvedValueOnce(jsonResponse(entry));

			await api.getEntry('test-entry', { kb: 'kb', with_links: true });
			const url = mockFetch.mock.calls[0][0] as string;
			expect(url).toContain('/api/entries/test-entry');
			expect(url).toContain('with_links=true');
		});
	});

	describe('createEntry', () => {
		it('sends POST with JSON body', async () => {
			mockFetch.mockResolvedValueOnce(jsonResponse({ created: true, id: 'new-entry', kb_name: 'kb', file_path: '/tmp/new.md' }));

			await api.createEntry({ kb: 'kb', title: 'New', body: 'Content', tags: ['test'] });
			expect(mockFetch).toHaveBeenCalledWith('/api/entries', expect.objectContaining({
				method: 'POST',
				body: expect.stringContaining('"title":"New"')
			}));
		});
	});

	describe('updateEntry', () => {
		it('sends PUT with JSON body', async () => {
			mockFetch.mockResolvedValueOnce(jsonResponse({ updated: true, id: 'entry-1' }));

			await api.updateEntry('entry-1', { kb: 'kb', body: 'Updated' });
			expect(mockFetch).toHaveBeenCalledWith('/api/entries/entry-1', expect.objectContaining({
				method: 'PUT',
				body: expect.stringContaining('"body":"Updated"')
			}));
		});
	});

	describe('deleteEntry', () => {
		it('sends DELETE with kb query param', async () => {
			mockFetch.mockResolvedValueOnce(jsonResponse({ deleted: true, id: 'entry-1' }));

			await api.deleteEntry('entry-1', 'my-kb');
			const [url, opts] = mockFetch.mock.calls[0];
			expect(url).toContain('/api/entries/entry-1');
			expect(url).toContain('kb=my-kb');
			expect(opts.method).toBe('DELETE');
		});
	});

	describe('error handling', () => {
		it('throws ApiError on non-OK response', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				statusText: 'Not Found',
				json: () => Promise.resolve({ detail: { code: 'NOT_FOUND', message: 'Entry not found' } })
			});

			await expect(api.getEntry('missing')).rejects.toThrow(ApiError);
		});

		it('includes status code in ApiError', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				statusText: 'Unauthorized',
				json: () => Promise.resolve({ detail: 'Invalid API key' })
			});

			try {
				await api.listKBs();
			} catch (e) {
				expect(e).toBeInstanceOf(ApiError);
				expect((e as ApiError).status).toBe(401);
			}
		});
	});

	describe('getTags', () => {
		it('passes kb filter', async () => {
			mockFetch.mockResolvedValueOnce(jsonResponse({ count: 2, tags: [{ name: 'a', count: 5 }] }));
			await api.getTags('my-kb');
			expect(mockFetch.mock.calls[0][0]).toContain('kb=my-kb');
		});
	});

	describe('syncIndex', () => {
		it('sends POST to /api/index/sync', async () => {
			mockFetch.mockResolvedValueOnce(jsonResponse({ synced: true, added: 1, updated: 0, removed: 0 }));
			const result = await api.syncIndex();
			expect(result.synced).toBe(true);
			expect(mockFetch.mock.calls[0][1].method).toBe('POST');
		});
	});
});
