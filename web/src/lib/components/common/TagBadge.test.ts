import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import TagBadge from './TagBadge.svelte';

describe('TagBadge', () => {
	it('renders the tag text', () => {
		render(TagBadge, { props: { tag: 'immigration' } });
		expect(screen.getByText('immigration')).toBeInTheDocument();
	});

	it('has badge styling', () => {
		render(TagBadge, { props: { tag: 'test' } });
		const el = screen.getByText('test');
		expect(el.className).toContain('rounded-full');
	});
});
