/**
 * Typed fetch wrapper for the Pyrite REST API.
 *
 * In development, Vite proxies /api to the FastAPI backend.
 * In production, both are served from the same origin.
 */

import type {
	AIAutoTagResponse,
	AILinkSuggestResponse,
	AIStatusResponse,
	AISummarizeResponse,
	CreateEntryRequest,
	CreateResponse,
	DailyDatesResponse,
	DeleteResponse,
	EntryListResponse,
	EntryResponse,
	EntryTitlesResponse,
	EntryTypesResponse,
	GraphResponse,
	KBListResponse,
	RenderedTemplate,
	ReorderStarredRequest,
	ReorderStarredResponse,
	ResolveResponse,
	SearchResponse,
	SettingResponse,
	SettingsResponse,
	StarEntryResponse,
	StarredEntryListResponse,
	StatsResponse,
	TagsResponse,
	TagTreeResponse,
	TemplateDetail,
	TemplateListResponse,
	TimelineResponse,
	UnstarEntryResponse,
	UpdateEntryRequest,
	UpdateResponse
} from './types';

class ApiClient {
	private baseUrl: string;

	constructor(baseUrl = '') {
		this.baseUrl = baseUrl;
	}

	private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
		const url = `${this.baseUrl}${path}`;
		const res = await fetch(url, {
			headers: {
				'Content-Type': 'application/json',
				...options.headers
			},
			...options
		});

		if (!res.ok) {
			const error = await res.json().catch(() => ({ message: res.statusText }));
			throw new ApiError(res.status, error.detail ?? error.message ?? res.statusText);
		}

		return res.json();
	}

	// Knowledge Bases
	async listKBs(): Promise<KBListResponse> {
		return this.request('/api/kbs');
	}

	// Search
	async search(
		query: string,
		options: {
			kb?: string;
			type?: string;
			tags?: string;
			limit?: number;
			mode?: 'keyword' | 'semantic' | 'hybrid';
		} = {}
	): Promise<SearchResponse> {
		const params = new URLSearchParams({ q: query });
		if (options.kb) params.set('kb', options.kb);
		if (options.type) params.set('type', options.type);
		if (options.tags) params.set('tags', options.tags);
		if (options.limit) params.set('limit', String(options.limit));
		if (options.mode) params.set('mode', options.mode);
		return this.request(`/api/search?${params}`);
	}

	// Entries
	async listEntries(options: {
		kb?: string;
		entry_type?: string;
		tag?: string;
		sort_by?: string;
		sort_order?: string;
		limit?: number;
		offset?: number;
	} = {}): Promise<EntryListResponse> {
		const params = new URLSearchParams();
		if (options.kb) params.set('kb', options.kb);
		if (options.entry_type) params.set('entry_type', options.entry_type);
		if (options.tag) params.set('tag', options.tag);
		if (options.sort_by) params.set('sort_by', options.sort_by);
		if (options.sort_order) params.set('sort_order', options.sort_order);
		if (options.limit) params.set('limit', String(options.limit));
		if (options.offset) params.set('offset', String(options.offset));
		const qs = params.toString();
		return this.request(`/api/entries${qs ? `?${qs}` : ''}`);
	}

	async getEntryTypes(kb?: string): Promise<EntryTypesResponse> {
		const params = kb ? `?kb=${encodeURIComponent(kb)}` : '';
		return this.request(`/api/entries/types${params}`);
	}

	async getEntry(id: string, options: { kb?: string; with_links?: boolean } = {}): Promise<EntryResponse> {
		const params = new URLSearchParams();
		if (options.kb) params.set('kb', options.kb);
		if (options.with_links) params.set('with_links', 'true');
		const qs = params.toString();
		return this.request(`/api/entries/${encodeURIComponent(id)}${qs ? `?${qs}` : ''}`);
	}

	async createEntry(req: CreateEntryRequest): Promise<CreateResponse> {
		return this.request('/api/entries', {
			method: 'POST',
			body: JSON.stringify(req)
		});
	}

	async updateEntry(id: string, req: UpdateEntryRequest): Promise<UpdateResponse> {
		return this.request(`/api/entries/${encodeURIComponent(id)}`, {
			method: 'PUT',
			body: JSON.stringify(req)
		});
	}

	async deleteEntry(id: string, kb: string): Promise<DeleteResponse> {
		return this.request(`/api/entries/${encodeURIComponent(id)}?kb=${encodeURIComponent(kb)}`, {
			method: 'DELETE'
		});
	}

	// Wikilinks
	async getEntryTitles(options: { kb?: string; q?: string; limit?: number } = {}): Promise<EntryTitlesResponse> {
		const params = new URLSearchParams();
		if (options.kb) params.set('kb', options.kb);
		if (options.q) params.set('q', options.q);
		if (options.limit) params.set('limit', String(options.limit));
		const qs = params.toString();
		return this.request(`/api/entries/titles${qs ? `?${qs}` : ''}`);
	}

	async resolveEntry(target: string, kb?: string): Promise<ResolveResponse> {
		const params = new URLSearchParams({ target });
		if (kb) params.set('kb', kb);
		return this.request(`/api/entries/resolve?${params}`);
	}

	// Tags
	async getTags(kb?: string, prefix?: string): Promise<TagsResponse> {
		const params = new URLSearchParams();
		if (kb) params.set('kb', kb);
		if (prefix) params.set('prefix', prefix);
		const qs = params.toString();
		return this.request(`/api/tags${qs ? `?${qs}` : ''}`);
	}

	async getTagTree(kb?: string): Promise<TagTreeResponse> {
		const params = kb ? `?kb=${encodeURIComponent(kb)}` : '';
		return this.request(`/api/tags/tree${params}`);
	}

	// Timeline
	async getTimeline(options: {
		date_from?: string;
		date_to?: string;
		min_importance?: number;
		limit?: number;
	} = {}): Promise<TimelineResponse> {
		const params = new URLSearchParams();
		if (options.date_from) params.set('date_from', options.date_from);
		if (options.date_to) params.set('date_to', options.date_to);
		if (options.min_importance) params.set('min_importance', String(options.min_importance));
		if (options.limit) params.set('limit', String(options.limit));
		const qs = params.toString();
		return this.request(`/api/timeline${qs ? `?${qs}` : ''}`);
	}

	// Stats
	async getStats(): Promise<StatsResponse> {
		return this.request('/api/stats');
	}

	// Index sync
	async syncIndex(): Promise<{ synced: boolean; added: number; updated: number; removed: number }> {
		return this.request('/api/index/sync', { method: 'POST' });
	}

	// Starred Entries
	async getStarredEntries(kb?: string): Promise<StarredEntryListResponse> {
		const params = kb ? `?kb=${encodeURIComponent(kb)}` : '';
		return this.request(`/api/starred${params}`);
	}

	async starEntry(entryId: string, kbName: string): Promise<StarEntryResponse> {
		return this.request('/api/starred', {
			method: 'POST',
			body: JSON.stringify({ entry_id: entryId, kb_name: kbName })
		});
	}

	async unstarEntry(entryId: string, kb?: string): Promise<UnstarEntryResponse> {
		const params = kb ? `?kb=${encodeURIComponent(kb)}` : '';
		return this.request(`/api/starred/${encodeURIComponent(entryId)}${params}`, {
			method: 'DELETE'
		});
	}

	async reorderStarred(entries: ReorderStarredRequest['entries']): Promise<ReorderStarredResponse> {
		return this.request('/api/starred/reorder', {
			method: 'PUT',
			body: JSON.stringify({ entries })
		});
	}

	// Templates
	async getTemplates(kbName: string): Promise<TemplateListResponse> {
		return this.request(`/api/kbs/${encodeURIComponent(kbName)}/templates`);
	}

	async getTemplate(kbName: string, templateName: string): Promise<TemplateDetail> {
		return this.request(
			`/api/kbs/${encodeURIComponent(kbName)}/templates/${encodeURIComponent(templateName)}`
		);
	}

	async renderTemplate(
		kbName: string,
		templateName: string,
		variables: Record<string, string> = {}
	): Promise<RenderedTemplate> {
		return this.request(
			`/api/kbs/${encodeURIComponent(kbName)}/templates/${encodeURIComponent(templateName)}/render`,
			{
				method: 'POST',
				body: JSON.stringify({ variables })
			}
		);
	}

	// Daily Notes
	async getDailyNote(date: string, kb: string): Promise<EntryResponse> {
		return this.request(`/api/daily/${date}?kb=${encodeURIComponent(kb)}`);
	}

	async getDailyDates(kb: string, month?: string): Promise<DailyDatesResponse> {
		const params = new URLSearchParams({ kb });
		if (month) params.set('month', month);
		return this.request(`/api/daily/dates?${params}`);
	}

	// Settings
	async getSettings(): Promise<SettingsResponse> {
		return this.request('/api/settings');
	}

	async setSetting(key: string, value: string): Promise<SettingResponse> {
		return this.request(`/api/settings/${encodeURIComponent(key)}`, {
			method: 'PUT',
			body: JSON.stringify({ value })
		});
	}

	async bulkUpdateSettings(settings: Record<string, string>): Promise<SettingsResponse> {
		return this.request('/api/settings', {
			method: 'PUT',
			body: JSON.stringify({ settings })
		});
	}

	// AI
	async getAIStatus(): Promise<AIStatusResponse> {
		return this.request('/api/ai/status');
	}

	async aiSummarize(entryId: string, kbName: string): Promise<AISummarizeResponse> {
		return this.request('/api/ai/summarize', {
			method: 'POST',
			body: JSON.stringify({ entry_id: entryId, kb_name: kbName })
		});
	}

	async aiAutoTag(entryId: string, kbName: string): Promise<AIAutoTagResponse> {
		return this.request('/api/ai/auto-tag', {
			method: 'POST',
			body: JSON.stringify({ entry_id: entryId, kb_name: kbName })
		});
	}

	// Graph
	async getGraph(options: {
		center?: string;
		center_kb?: string;
		kb?: string;
		type?: string;
		depth?: number;
		limit?: number;
	} = {}): Promise<GraphResponse> {
		const params = new URLSearchParams();
		if (options.center) params.set('center', options.center);
		if (options.center_kb) params.set('center_kb', options.center_kb);
		if (options.kb) params.set('kb', options.kb);
		if (options.type) params.set('type', options.type);
		if (options.depth) params.set('depth', String(options.depth));
		if (options.limit) params.set('limit', String(options.limit));
		const qs = params.toString();
		return this.request(`/api/graph${qs ? `?${qs}` : ''}`);
	}

	async aiSuggestLinks(entryId: string, kbName: string): Promise<AILinkSuggestResponse> {
		return this.request('/api/ai/suggest-links', {
			method: 'POST',
			body: JSON.stringify({ entry_id: entryId, kb_name: kbName })
		});
	}
}

export class ApiError extends Error {
	status: number;
	detail: string;

	constructor(status: number, detail: string) {
		super(`API Error ${status}: ${detail}`);
		this.status = status;
		this.detail = detail;
	}
}

export const api = new ApiClient();
