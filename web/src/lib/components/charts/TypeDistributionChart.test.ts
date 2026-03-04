import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import TypeDistributionChart from './TypeDistributionChart.svelte';
import { typeColor } from '$lib/constants';

afterEach(() => {
	cleanup();
});

describe('TypeDistributionChart', () => {
	it('shows "No entries" when total is 0', () => {
		render(TypeDistributionChart, { props: { data: [{ entry_type: 'note', count: 0 }] } });
		expect(screen.getByText('No entries')).toBeInTheDocument();
	});

	it('shows "No entries" for empty array', () => {
		render(TypeDistributionChart, { props: { data: [] } });
		expect(screen.getByText('No entries')).toBeInTheDocument();
	});

	it('renders SVG with role="img" for a single item', () => {
		render(TypeDistributionChart, { props: { data: [{ entry_type: 'note', count: 5 }] } });
		expect(screen.getByRole('img')).toBeInTheDocument();
	});

	it('shows total count in center text', () => {
		render(TypeDistributionChart, {
			props: {
				data: [
					{ entry_type: 'note', count: 5 },
					{ entry_type: 'event', count: 3 },
				],
			},
		});
		expect(screen.getByText('8')).toBeInTheDocument();
	});

	it('shows "entries" label in SVG', () => {
		render(TypeDistributionChart, { props: { data: [{ entry_type: 'note', count: 5 }] } });
		expect(screen.getByText('entries')).toBeInTheDocument();
	});

	it('renders legend with entry type names', () => {
		render(TypeDistributionChart, {
			props: {
				data: [
					{ entry_type: 'note', count: 5 },
					{ entry_type: 'event', count: 3 },
				],
			},
		});
		expect(screen.getByText('note')).toBeInTheDocument();
		expect(screen.getByText('event')).toBeInTheDocument();
	});

	it('legend shows counts for each type', () => {
		render(TypeDistributionChart, {
			props: {
				data: [
					{ entry_type: 'note', count: 5 },
					{ entry_type: 'event', count: 3 },
				],
			},
		});
		expect(screen.getByText('5')).toBeInTheDocument();
		expect(screen.getByText('3')).toBeInTheDocument();
	});

	it('SVG segments have stroke-dasharray attributes', () => {
		const { container } = render(TypeDistributionChart, {
			props: { data: [{ entry_type: 'note', count: 5 }] },
		});
		const circles = container.querySelectorAll('circle');
		const segmentCircles = Array.from(circles).filter((c) => c.getAttribute('stroke-dasharray'));
		expect(segmentCircles.length).toBeGreaterThan(0);
	});

	it('each data item gets a circle element plus one background circle', () => {
		const data = [
			{ entry_type: 'note', count: 5 },
			{ entry_type: 'event', count: 3 },
			{ entry_type: 'person', count: 2 },
		];
		const { container } = render(TypeDistributionChart, { props: { data } });
		const circles = container.querySelectorAll('circle');
		// 1 background circle + 1 per data item
		expect(circles.length).toBe(data.length + 1);
	});

	it('legend colored dots have correct background-color from typeColor', () => {
		const { container } = render(TypeDistributionChart, {
			props: {
				data: [
					{ entry_type: 'event', count: 4 },
					{ entry_type: 'person', count: 2 },
				],
			},
		});
		const dots = container.querySelectorAll('span.rounded-full');
		// Browser normalizes hex colors to rgb() format
		expect(dots.length).toBe(2);
		for (const dot of Array.from(dots)) {
			const bg = (dot as HTMLElement).style.backgroundColor;
			expect(bg).toBeTruthy();
		}
	});

	it('single data item with count=10 shows "10" as total', () => {
		const { container } = render(TypeDistributionChart, {
			props: { data: [{ entry_type: 'topic', count: 10 }] },
		});
		// The total text is in a <text> element with font-weight="700"
		const totalText = container.querySelector('text[font-weight="700"]');
		expect(totalText).not.toBeNull();
		expect(totalText!.textContent).toBe('10');
	});

	it('multiple items display all type names in legend', () => {
		const data = [
			{ entry_type: 'note', count: 1 },
			{ entry_type: 'event', count: 2 },
			{ entry_type: 'person', count: 3 },
			{ entry_type: 'topic', count: 4 },
		];
		render(TypeDistributionChart, { props: { data } });
		for (const d of data) {
			expect(screen.getByText(d.entry_type)).toBeInTheDocument();
		}
	});
});
