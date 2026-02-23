import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import TemplatePicker from './TemplatePicker.svelte';

afterEach(() => {
	cleanup();
});

const sampleTemplates = [
	{ name: 'Meeting Note', description: 'Template for meeting notes', entry_type: 'meeting' },
	{ name: 'Research Brief', description: 'Quick research summary', entry_type: 'note' }
];

describe('TemplatePicker', () => {
	it('renders template list with names and descriptions', () => {
		const onselect = vi.fn();
		render(TemplatePicker, { props: { templates: sampleTemplates, onselect } });

		expect(screen.getByText('Meeting Note')).toBeInTheDocument();
		expect(screen.getByText('Template for meeting notes')).toBeInTheDocument();
		expect(screen.getByText('Research Brief')).toBeInTheDocument();
		expect(screen.getByText('Quick research summary')).toBeInTheDocument();
	});

	it('always shows Blank Entry option', () => {
		const onselect = vi.fn();
		render(TemplatePicker, { props: { templates: sampleTemplates, onselect } });

		expect(screen.getAllByText('Blank Entry').length).toBeGreaterThanOrEqual(1);
	});

	it('calls onselect with null for blank entry', async () => {
		const onselect = vi.fn();
		render(TemplatePicker, { props: { templates: sampleTemplates, onselect } });

		const blankButtons = screen.getAllByTestId('template-blank');
		await fireEvent.click(blankButtons[0]);
		expect(onselect).toHaveBeenCalledWith(null);
	});

	it('calls onselect with template name when a template is selected', async () => {
		const onselect = vi.fn();
		render(TemplatePicker, { props: { templates: sampleTemplates, onselect } });

		const options = screen.getAllByTestId('template-option');
		await fireEvent.click(options[0]);
		expect(onselect).toHaveBeenCalledWith('Meeting Note');
	});

	it('shows loading state', () => {
		const onselect = vi.fn();
		render(TemplatePicker, { props: { templates: [], loading: true, onselect } });

		expect(screen.getByText('Loading templates...')).toBeInTheDocument();
	});

	it('shows entry type badge', () => {
		const onselect = vi.fn();
		render(TemplatePicker, { props: { templates: sampleTemplates, onselect } });

		expect(screen.getAllByText('meeting').length).toBeGreaterThanOrEqual(1);
	});

	it('shows empty message when no templates available', () => {
		const onselect = vi.fn();
		render(TemplatePicker, { props: { templates: [], onselect } });

		expect(screen.getByText('No templates available for this KB.')).toBeInTheDocument();
	});
});
