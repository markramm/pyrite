import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import TypeChoice from './TypeChoice.svelte';

afterEach(() => {
	cleanup();
});

const declaredTypes = ['adr', 'backlog_item', 'component', 'standard'];
const allTypes = [...declaredTypes, 'note', 'event', 'person'];

describe('TypeChoice (#392, round 1 cold read)', () => {
	it('offers only the declared types when the KB declares any', () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: '', onchange }
		});

		const select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		const optionValues = Array.from(select.options)
			.map((o) => o.value)
			.filter((v) => v !== '');
		expect(optionValues.sort()).toEqual([...declaredTypes].sort());
		expect(optionValues).not.toContain('note');
	});

	it('does NOT preselect an arbitrary declared type: starts unchosen with a placeholder', () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: '', onchange }
		});

		const select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		expect(select.value).toBe('');
		expect(screen.getByText('Choose a type…')).toBeInTheDocument();
	});

	it('reports an unchosen value on mount so the caller can disable submit', () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: '', onchange }
		});
		// No onchange call implies "not chosen"; the page starts entryType at ''.
		expect(onchange).not.toHaveBeenCalled();
	});

	it('auto-selects the single type when the KB declares exactly one', () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: ['adr'], value: '', onchange }
		});

		expect(onchange).toHaveBeenCalledWith(
			expect.objectContaining({ entryType: 'adr', allowUndeclared: false })
		);
	});

	it('offers every type when the KB declares none', () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: [], value: 'note', onchange }
		});

		const select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		const optionValues = Array.from(select.options).map((o) => o.value);
		expect(optionValues.sort()).toEqual([...allTypes].sort());
	});

	it('does not show the undeclared-type override when the KB declares none', () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: [], value: 'note', onchange }
		});

		expect(screen.queryByTestId('allow-undeclared-toggle')).not.toBeInTheDocument();
	});

	it('shows an explicit override control when the KB declares types', () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: 'adr', onchange }
		});

		expect(screen.getByTestId('allow-undeclared-toggle')).toBeInTheDocument();
	});

	it('marks the override toggle with aria-pressed reflecting its state', async () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: 'adr', onchange }
		});

		const toggle = screen.getByTestId('allow-undeclared-toggle');
		expect(toggle).toHaveAttribute('aria-pressed', 'false');
		await fireEvent.click(toggle);
		expect(toggle).toHaveAttribute('aria-pressed', 'true');
	});

	it('reveals every type only after the override is used, and that is the only thing setting allow_undeclared', async () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: 'adr', onchange }
		});

		// Before the override: no allow_undeclared call yet.
		expect(onchange).not.toHaveBeenCalledWith(expect.objectContaining({ allowUndeclared: true }));

		const toggle = screen.getByTestId('allow-undeclared-toggle');
		await fireEvent.click(toggle);

		const select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		const optionValues = Array.from(select.options)
			.map((o) => o.value)
			.filter((v) => v !== '');
		expect(optionValues.sort()).toEqual([...allTypes].sort());

		// Selecting a type after the override reveals it must report allowUndeclared: true.
		await fireEvent.change(select, { target: { value: 'note' } });
		expect(onchange).toHaveBeenCalledWith(
			expect.objectContaining({ entryType: 'note', allowUndeclared: true })
		);
	});

	it('never reports allowUndeclared true without the override being used', async () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: 'adr', onchange }
		});

		const select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		await fireEvent.change(select, { target: { value: 'backlog_item' } });
		expect(onchange).toHaveBeenCalledWith(
			expect.objectContaining({ entryType: 'backlog_item', allowUndeclared: false })
		);
	});

	it('toggling the override off returns to only declared types', async () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: 'adr', onchange }
		});

		const toggle = screen.getByTestId('allow-undeclared-toggle');
		await fireEvent.click(toggle);
		await fireEvent.click(toggle);

		const select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		const optionValues = Array.from(select.options)
			.map((o) => o.value)
			.filter((v) => v !== '');
		expect(optionValues.sort()).toEqual([...declaredTypes].sort());
	});

	it('the value the KB does not declare is pre-selected and visible when the override is forced on (template path)', () => {
		// The New-entry form's template path: a template names an undeclared
		// type; the page shows it selected with the override already engaged
		// so the user sees and can change it (round-1 blocker 1).
		const onchange = vi.fn();
		render(TypeChoice, {
			props: {
				types: allTypes,
				declared: declaredTypes,
				value: 'note',
				forceOverride: true,
				onchange
			}
		});

		const select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		expect(select.value).toBe('note');
		const toggle = screen.getByTestId('allow-undeclared-toggle');
		expect(toggle).toHaveAttribute('aria-pressed', 'true');
	});

	it('forceOverride shows the undeclared type but never calls onchange on its own -- the page must keep allow_undeclared false until the user acts', () => {
		// Round-1 blocker 1: a template naming an undeclared type must not
		// have the flag set FOR the user. TypeChoice only shows the picker
		// pre-armed; the page's own allowUndeclared state must start false
		// and only flip when this component reports a REAL choice.
		const onchange = vi.fn();
		render(TypeChoice, {
			props: {
				types: allTypes,
				declared: declaredTypes,
				value: 'note',
				forceOverride: true,
				onchange
			}
		});

		expect(onchange).not.toHaveBeenCalled();
	});

	it('uses a caller-supplied id instead of a hard-coded one', () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: 'adr', onchange, id: 'clip-entry-type' }
		});

		expect(screen.getByTestId('entry-type-select')).toHaveAttribute('id', 'clip-entry-type');
	});

	it('shows the type description in each option', () => {
		const onchange = vi.fn();
		const typeDescriptions = { adr: 'Architecture decision record' };
		render(TypeChoice, {
			props: {
				types: allTypes,
				declared: declaredTypes,
				value: 'adr',
				onchange,
				typeDescriptions
			}
		});

		expect(screen.getByText(/adr.*Architecture decision record/)).toBeInTheDocument();
	});
});
