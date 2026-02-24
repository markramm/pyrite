/** AI chat store: manages chat messages and SSE streaming */

import type { ChatMessage, ChatSourceEntry } from '$lib/api/types';

interface EntryContext {
	id: string;
	kb: string;
	title: string;
}

class AIChatStore {
	messages = $state<ChatMessage[]>([]);
	loading = $state(false);
	error = $state<string | null>(null);
	sources = $state<ChatSourceEntry[]>([]);
	entryContext = $state<EntryContext | null>(null);
	private abortController: AbortController | null = null;

	async send(content: string, kb?: string) {
		this.error = null;
		this.sources = [];

		// Add user message
		this.messages = [...this.messages, { role: 'user', content }];
		// Add empty assistant message to stream into
		this.messages = [...this.messages, { role: 'assistant', content: '' }];
		this.loading = true;

		try {
			this.abortController = new AbortController();
			const body: Record<string, unknown> = {
				messages: this.messages.slice(0, -1) // exclude the empty assistant msg
			};
			if (kb) body.kb = kb;
			if (this.entryContext) {
				body.entry_id = this.entryContext.id;
				if (!kb) body.kb = this.entryContext.kb;
			}

			const res = await fetch('/api/ai/chat', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body),
				signal: this.abortController.signal
			});

			if (!res.ok) {
				const err = await res.json().catch(() => ({ detail: res.statusText }));
				throw new Error(err.detail?.message ?? err.detail ?? res.statusText);
			}

			const reader = res.body?.getReader();
			if (!reader) throw new Error('No response body');

			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() ?? '';

				for (const line of lines) {
					if (!line.startsWith('data: ')) continue;
					const jsonStr = line.slice(6);
					try {
						const event = JSON.parse(jsonStr);
						if (event.type === 'token') {
							// Update the last message (assistant) content
							const msgs = [...this.messages];
							const last = msgs[msgs.length - 1];
							msgs[msgs.length - 1] = { ...last, content: last.content + event.content };
							this.messages = msgs;
						} else if (event.type === 'sources') {
							this.sources = event.entries ?? [];
						} else if (event.type === 'error') {
							this.error = event.message;
						}
					} catch {
						// skip malformed events
					}
				}
			}
		} catch (e) {
			if (e instanceof DOMException && e.name === 'AbortError') return;
			this.error = e instanceof Error ? e.message : 'Chat failed';
			// Remove the empty assistant message on error
			if (this.messages.length > 0 && this.messages[this.messages.length - 1].content === '') {
				this.messages = this.messages.slice(0, -1);
			}
		} finally {
			this.loading = false;
			this.abortController = null;
		}
	}

	stop() {
		this.abortController?.abort();
	}

	clear() {
		this.messages = [];
		this.sources = [];
		this.error = null;
		this.entryContext = null;
	}
}

export const aiChatStore = new AIChatStore();
