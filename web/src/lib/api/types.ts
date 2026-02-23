/** TypeScript types matching Pyrite Pydantic schemas */

export interface KBInfo {
	name: string;
	type: string;
	path: string;
	entries: number;
	indexed: boolean;
}

export interface KBListResponse {
	kbs: KBInfo[];
	total: number;
}

export interface SearchResult {
	id: string;
	kb_name: string;
	entry_type: string;
	title: string;
	snippet?: string;
	date?: string;
	importance?: number;
	tags: string[];
}

export interface SearchResponse {
	query: string;
	count: number;
	results: SearchResult[];
}

export interface EntryResponse {
	id: string;
	kb_name: string;
	entry_type: string;
	title: string;
	body?: string;
	summary?: string;
	date?: string;
	importance?: number;
	status?: string;
	tags: string[];
	participants: string[];
	sources: Record<string, unknown>[];
	outlinks: Record<string, unknown>[];
	backlinks: Record<string, unknown>[];
	file_path: string;
	created_at?: string;
	updated_at?: string;
}

export interface EntryListResponse {
	entries: EntryResponse[];
	total: number;
	limit: number;
	offset: number;
}

export interface CreateEntryRequest {
	kb: string;
	entry_type?: string;
	title: string;
	body?: string;
	date?: string;
	importance?: number;
	tags?: string[];
	participants?: string[];
	role?: string;
	metadata?: Record<string, unknown>;
}

export interface UpdateEntryRequest {
	kb: string;
	title?: string;
	body?: string;
	importance?: number;
	tags?: string[];
	metadata?: Record<string, unknown>;
}

export interface CreateResponse {
	created: boolean;
	id: string;
	kb_name: string;
	file_path: string;
}

export interface UpdateResponse {
	updated: boolean;
	id: string;
}

export interface DeleteResponse {
	deleted: boolean;
	id: string;
}

export interface TagCount {
	name: string;
	count: number;
}

export interface TagsResponse {
	count: number;
	tags: TagCount[];
}

export interface TimelineEvent {
	id: string;
	date: string;
	title: string;
	importance: number;
	tags: string[];
}

export interface TimelineResponse {
	count: number;
	date_from?: string;
	date_to?: string;
	events: TimelineEvent[];
}

export interface StatsResponse {
	total_entries: number;
	kbs: Record<string, unknown>;
	total_tags: number;
	total_links: number;
}

export interface ApiError {
	code: string;
	message: string;
	hint?: string;
}

// Wikilinks

export interface EntryTitle {
	id: string;
	title: string;
	kb_name: string;
	entry_type: string;
}

export interface EntryTitlesResponse {
	entries: EntryTitle[];
}

export interface ResolveResponse {
	resolved: boolean;
	entry: EntryTitle | null;
}

// Starred Entries

export interface StarredEntryItem {
	entry_id: string;
	kb_name: string;
	sort_order: number;
	created_at: string;
}

export interface StarredEntryListResponse {
	count: number;
	starred: StarredEntryItem[];
}

export interface StarEntryResponse {
	starred: boolean;
	entry_id: string;
	kb_name: string;
}

export interface UnstarEntryResponse {
	unstarred: boolean;
	entry_id: string;
}

export interface ReorderStarredItem {
	entry_id: string;
	kb_name: string;
	sort_order: number;
}

export interface ReorderStarredRequest {
	entries: ReorderStarredItem[];
}

export interface ReorderStarredResponse {
	reordered: boolean;
	count: number;
}

// Templates

export interface TemplateSummary {
	name: string;
	description: string;
	entry_type: string;
}

export interface TemplateListResponse {
	templates: TemplateSummary[];
	total: number;
}

export interface TemplateDetail {
	name: string;
	description: string;
	entry_type: string;
	frontmatter: Record<string, unknown>;
	body: string;
}

export interface RenderedTemplate {
	entry_type: string;
	frontmatter: Record<string, unknown>;
	body: string;
}

// Daily Notes

export interface DailyDatesResponse {
	dates: string[];
}
