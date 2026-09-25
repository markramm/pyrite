import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import TypeChoice from './TypeChoice.svelte';

afterEach(() => {
	cleanup();
});

const declaredTypes = ['adr', 'backlog_item', 'component', 'standard'];
const allTypes = [...declaredTypes, 'note', 'event', 'person'];

describe('TypeChoice (#392)', () => {
	it('offers only the declared types when the KB declares any', () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: 'adr', onchange }
		});

		const select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		const optionValues = Array.from(select.options).map((o) => o.value);
		expect(optionValues.sort()).toEqual([...declaredTypes].sort());
		expect(optionValues).not.toContain('note');
	});

	it('defaults to a declared type when the KB declares any', () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: 'adr', onchange }
		});

		const select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		expect(declaredTypes).toContain(select.value);
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

	it('reveals every type only after the override is used, and that is the only thing setting allow_undeclared', async () => {
		const onchange = vi.fn();
		render(TypeChoice, {
			props: { types: allTypes, declared: declaredTypes, value: 'adr', onchange }
		});

		// Before the override: only declared types, no allow_undeclared call yet.
		expect(onchange).not.toHaveBeenCalledWith(expect.objectContaining({ allowUndeclared: true }));

		const toggle = screen.getByTestId('allow-undeclared-toggle');
		await fireEvent.click(toggle);

		const select = screen.getByTestId('entry-type-select') as HTMLSelectElement;
		const optionValues = Array.from(select.options).map((o) => o.value);
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
		const optionValues = Array.from(select.options).map((o) => o.value);
		expect(optionValues.sort()).toEqual([...declaredTypes].sort());
	});
});
