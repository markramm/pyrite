import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';

const mockMessages: Array<{ role: string; content: string }> = [];
const mockSources: Array<{ id: string; title: string; snippet?: string }> = [];
let mockLoading = false;
let mockError: string | null = null;
let mockEntryContext: { title: string } | null = null;

vi.mock('$lib/stores/ai.svelte', () => ({
	aiChatStore: {
		get messages() {
			return mockMessages;
		},
		get sources() {
			return mockSources;
		},
		get loading() {
			return mockLoading;
		},
		get error() {
			return mockError;
		},
		get entryContext() {
			return mockEntryContext;
		},
		send: vi.fn(),
		clear: vi.fn()
	}
}));

vi.mock('$lib/stores/ui.svelte', () => ({
	uiStore: {
		chatPanelOpen: true,
		toast: vi.fn()
	}
}));

import ChatSidebar from './ChatSidebar.svelte';
import { aiChatStore } from '$lib/stores/ai.svelte';

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
	mockMessages.length = 0;
	mockSources.length = 0;
	mockLoading = false;
	mockError = null;
	mockEntryContext = null;
});

describe('ChatSidebar', () => {
	it('shows "Chat with KB" header', () => {
		render(ChatSidebar);
		expect(screen.getByText('Chat with KB')).toBeInTheDocument();
	});

	it('shows empty state text when no messages', () => {
		render(ChatSidebar);
		expect(
			screen.getByText('Ask a question about your knowledge base.')
		).toBeInTheDocument();
	});

	it('renders user message with correct text', () => {
		mockMessages.push({ role: 'user', content: 'What is pyrite?' });
		render(ChatSidebar);
		expect(screen.getByText('What is pyrite?')).toBeInTheDocument();
	});

	it('renders assistant message with correct text', () => {
		mockMessages.push({ role: 'assistant', content: 'Pyrite is a knowledge platform.' });
		render(ChatSidebar);
		expect(screen.getByText('Pyrite is a knowledge platform.')).toBeInTheDocument();
	});

	it('renders citations as clickable links', () => {
		mockMessages.push({
			role: 'assistant',
			content: 'See [[my-entry]] for details.'
		});
		const { container } = render(ChatSidebar);
		const link = container.querySelector('a[href="/entries/my-entry"]');
		expect(link).not.toBeNull();
		expect(link!.textContent).toBe('my-entry');
	});

	it('shows "Clear" button', () => {
		render(ChatSidebar);
		expect(screen.getByText('Clear')).toBeInTheDocument();
	});

	it('shows placeholder text on textarea', () => {
		render(ChatSidebar);
		expect(screen.getByPlaceholderText('Ask a question...')).toBeInTheDocument();
	});

	it('send button shows "Send" text', () => {
		render(ChatSidebar);
		expect(screen.getByText('Send')).toBeInTheDocument();
	});

	it('shows error banner when error is set', () => {
		mockError = 'Network failure';
		render(ChatSidebar);
		expect(screen.getByText('Network failure')).toBeInTheDocument();
	});

	it('shows sources heading and source links when sources are present', () => {
		mockMessages.push({ role: 'assistant', content: 'Here is an answer.' });
		mockSources.push({ id: 'entry-1', title: 'First Source', snippet: 'A snippet' });
		render(ChatSidebar);
		expect(screen.getByText('Sources')).toBeInTheDocument();
		expect(screen.getByText('First Source')).toBeInTheDocument();
	});
});
