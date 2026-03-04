import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/svelte';

vi.mock('$lib/api/client', () => ({
	api: {
		aiSummarize: vi.fn(),
		aiAutoTag: vi.fn(),
		aiSuggestLinks: vi.fn(),
	}
}));

vi.mock('$lib/stores/ui.svelte', () => ({
	uiStore: {
		toast: vi.fn(),
		chatPanelOpen: false,
	}
}));

vi.mock('$lib/stores/ai.svelte', () => ({
	aiChatStore: {
		clear: vi.fn(),
		entryContext: null,
	}
}));

import { api } from '$lib/api/client';
import { uiStore } from '$lib/stores/ui.svelte';
import AIPanelTestWrapper from './AIPanelTestWrapper.svelte';

const mockSummarize = vi.mocked(api.aiSummarize);
const mockAutoTag = vi.mocked(api.aiAutoTag);
const mockSuggestLinks = vi.mocked(api.aiSuggestLinks);
const mockToast = vi.mocked(uiStore.toast);

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('AIPanel', () => {
	it('renders the AI button', () => {
		render(AIPanelTestWrapper);
		expect(screen.getByText('AI')).toBeInTheDocument();
	});

	it('clicking AI button opens dropdown menu', async () => {
		render(AIPanelTestWrapper);
		const aiButton = screen.getByText('AI');
		await fireEvent.click(aiButton);
		expect(screen.getByText('Summarize')).toBeInTheDocument();
	});

	it('menu shows Summarize option', async () => {
		render(AIPanelTestWrapper);
		await fireEvent.click(screen.getByText('AI'));
		expect(screen.getByText('Summarize')).toBeInTheDocument();
	});

	it('menu shows Suggest Tags option', async () => {
		render(AIPanelTestWrapper);
		await fireEvent.click(screen.getByText('AI'));
		expect(screen.getByText('Suggest Tags')).toBeInTheDocument();
	});

	it('menu shows Find Links option', async () => {
		render(AIPanelTestWrapper);
		await fireEvent.click(screen.getByText('AI'));
		expect(screen.getByText('Find Links')).toBeInTheDocument();
	});

	it('menu shows Ask AI about this option', async () => {
		render(AIPanelTestWrapper);
		await fireEvent.click(screen.getByText('AI'));
		expect(screen.getByText('Ask AI about this')).toBeInTheDocument();
	});

	it('clicking Summarize calls api.aiSummarize', async () => {
		mockSummarize.mockResolvedValue({ summary: 'A test summary' });
		render(AIPanelTestWrapper);
		await fireEvent.click(screen.getByText('AI'));
		await fireEvent.click(screen.getByText('Summarize'));
		await waitFor(() => {
			expect(mockSummarize).toHaveBeenCalledWith('test-entry', 'test-kb');
		});
	});

	it('summary result displays text', async () => {
		mockSummarize.mockResolvedValue({ summary: 'This is a summary' });
		render(AIPanelTestWrapper);
		await fireEvent.click(screen.getByText('AI'));
		await fireEvent.click(screen.getByText('Summarize'));
		await waitFor(() => {
			expect(screen.getByText('AI Summary')).toBeInTheDocument();
			expect(screen.getByText('This is a summary')).toBeInTheDocument();
		});
	});

	it('clicking Suggest Tags shows tag suggestions', async () => {
		mockAutoTag.mockResolvedValue({
			suggested_tags: [
				{ name: 'newtag', reason: 'relevant', is_new: true }
			]
		});
		render(AIPanelTestWrapper);
		await fireEvent.click(screen.getByText('AI'));
		await fireEvent.click(screen.getByText('Suggest Tags'));
		await waitFor(() => {
			expect(screen.getByText('Suggested Tags')).toBeInTheDocument();
			expect(screen.getByText('newtag')).toBeInTheDocument();
		});
	});

	it('clicking a suggested tag calls onTagsChanged', async () => {
		mockAutoTag.mockResolvedValue({
			suggested_tags: [
				{ name: 'newtag', reason: 'relevant', is_new: true }
			]
		});
		const onTagsChanged = vi.fn();
		render(AIPanelTestWrapper, { props: { tags: [], onTagsChanged } });
		await fireEvent.click(screen.getByText('AI'));
		await fireEvent.click(screen.getByText('Suggest Tags'));
		await waitFor(() => {
			expect(screen.getByText('newtag')).toBeInTheDocument();
		});
		await fireEvent.click(screen.getByText('newtag'));
		expect(onTagsChanged).toHaveBeenCalledWith(['newtag']);
	});

	it('error shows toast', async () => {
		mockSummarize.mockRejectedValue(new Error('API failure'));
		render(AIPanelTestWrapper);
		await fireEvent.click(screen.getByText('AI'));
		await fireEvent.click(screen.getByText('Summarize'));
		await waitFor(() => {
			expect(mockToast).toHaveBeenCalledWith('API failure', 'error');
		});
	});

	it('shows Processing... during loading', async () => {
		mockSummarize.mockReturnValue(new Promise(() => {}));
		render(AIPanelTestWrapper);
		await fireEvent.click(screen.getByText('AI'));
		await fireEvent.click(screen.getByText('Summarize'));
		await waitFor(() => {
			expect(screen.getByText('Processing...')).toBeInTheDocument();
		});
	});
});
