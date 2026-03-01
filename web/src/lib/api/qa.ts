/**
 * QA API client functions for the Pyrite REST API.
 */

export interface QAIssue {
	entry_id: string;
	kb_name: string;
	rule: string;
	severity: string;
	field: string | null;
	message: string;
}

export interface QAStatus {
	total_entries: number;
	total_issues: number;
	issues_by_severity: Record<string, number>;
	issues_by_rule: Record<string, number>;
}

export interface QAValidationKB {
	kb_name: string;
	total: number;
	checked: number;
	issues: QAIssue[];
}

export interface QAValidationAll {
	kbs: QAValidationKB[];
}

export interface QAValidationEntry {
	entry_id: string;
	kb_name: string;
	issues: QAIssue[];
}

export interface QACoverage {
	total: number;
	assessed: number;
	unassessed: number;
	coverage_pct: number;
	by_status: Record<string, number>;
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

export async function getQAStatus(kb?: string): Promise<QAStatus> {
	const params = new URLSearchParams();
	if (kb) params.set('kb', kb);
	const qs = params.toString();
	return request(`/api/qa/status${qs ? `?${qs}` : ''}`);
}

export async function getQAValidation(kb?: string): Promise<QAValidationKB | QAValidationAll> {
	const params = new URLSearchParams();
	if (kb) params.set('kb', kb);
	const qs = params.toString();
	return request(`/api/qa/validate${qs ? `?${qs}` : ''}`);
}

export async function getQAEntryValidation(entryId: string, kb: string): Promise<QAValidationEntry> {
	return request(`/api/qa/validate/${encodeURIComponent(entryId)}?kb=${encodeURIComponent(kb)}`);
}

export async function getQACoverage(kb: string): Promise<QACoverage> {
	return request(`/api/qa/coverage?kb=${encodeURIComponent(kb)}`);
}
