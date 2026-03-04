import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import OutlinePanel from './OutlinePanel.svelte';

afterEach(() => {
	cleanup();
});

describe('OutlinePanel', () => {
	it('renders "Outline" header text', () => {
		render(OutlinePanel, { props: { body: '' } });
		expect(screen.getByText('Outline')).toBeInTheDocument();
	});

	it('shows "No headings found." for empty body', () => {
		render(OutlinePanel, { props: { body: '' } });
		expect(screen.getByText('No headings found.')).toBeInTheDocument();
	});

	it('shows "No headings found." for body with no headings', () => {
		render(OutlinePanel, { props: { body: 'Just a paragraph.\nAnother line.' } });
		expect(screen.getByText('No headings found.')).toBeInTheDocument();
	});

	it('parses h1 heading', () => {
		render(OutlinePanel, { props: { body: '# Hello' } });
		expect(screen.getByText('Hello')).toBeInTheDocument();
	});

	it('parses multiple heading levels', () => {
		render(OutlinePanel, { props: { body: '# Title\n## Section\n### Subsection' } });
		expect(screen.getByText('Title')).toBeInTheDocument();
		expect(screen.getByText('Section')).toBeInTheDocument();
		expect(screen.getByText('Subsection')).toBeInTheDocument();
	});

	it('heading buttons have indentation via padding-left', () => {
		render(OutlinePanel, { props: { body: '## Indented' } });
		const btn = screen.getByText('Indented');
		expect(btn.getAttribute('style')).toContain('padding-left');
	});

	it('h1 has less padding than h2', () => {
		render(OutlinePanel, { props: { body: '# Top\n## Nested' } });
		const h1Btn = screen.getByText('Top');
		const h2Btn = screen.getByText('Nested');

		const h1Padding = parseFloat(h1Btn.getAttribute('style')!.match(/padding-left:\s*([\d.]+)/)?.[1] ?? '0');
		const h2Padding = parseFloat(h2Btn.getAttribute('style')!.match(/padding-left:\s*([\d.]+)/)?.[1] ?? '0');

		expect(h1Padding).toBeLessThan(h2Padding);
	});

	it('skips headings inside code blocks', () => {
		const body = '# Real\n```\n# Fake\n```\n## Also Real';
		render(OutlinePanel, { props: { body } });

		expect(screen.getByText('Real')).toBeInTheDocument();
		expect(screen.getByText('Also Real')).toBeInTheDocument();
		expect(screen.queryByText('Fake')).not.toBeInTheDocument();
	});

	it('generates correct slug for heading with spaces', () => {
		render(OutlinePanel, { props: { body: '# Hello World' } });
		const btn = screen.getByText('Hello World');
		expect(btn).toBeInTheDocument();
	});

	it('strips special characters from slug', () => {
		render(OutlinePanel, { props: { body: "# What's New?" } });
		const btn = screen.getByText("What's New?");
		expect(btn).toBeInTheDocument();
	});

	it('click on heading button calls scrollIntoView', async () => {
		render(OutlinePanel, { props: { body: '# Hello' } });

		const mockEl = { scrollIntoView: vi.fn() };
		vi.spyOn(document, 'getElementById').mockReturnValue(mockEl as any);

		const btn = screen.getByText('Hello');
		await fireEvent.click(btn);

		expect(document.getElementById).toHaveBeenCalledWith('hello');
		expect(mockEl.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' });

		vi.restoreAllMocks();
	});

	it('handles multiple code block fences correctly', () => {
		const body = '# Before\n```\n# Inside1\n```\n## Between\n```\n# Inside2\n```\n### After';
		render(OutlinePanel, { props: { body } });

		expect(screen.getByText('Before')).toBeInTheDocument();
		expect(screen.getByText('Between')).toBeInTheDocument();
		expect(screen.getByText('After')).toBeInTheDocument();
		expect(screen.queryByText('Inside1')).not.toBeInTheDocument();
		expect(screen.queryByText('Inside2')).not.toBeInTheDocument();
	});

	it('handles heading with trailing spaces', () => {
		render(OutlinePanel, { props: { body: '# Trailing   ' } });
		expect(screen.getByText('Trailing')).toBeInTheDocument();
	});

	it('handles empty lines between headings without issues', () => {
		render(OutlinePanel, { props: { body: '# First\n\n\n## Second\n\n### Third' } });
		expect(screen.getByText('First')).toBeInTheDocument();
		expect(screen.getByText('Second')).toBeInTheDocument();
		expect(screen.getByText('Third')).toBeInTheDocument();
	});
});
