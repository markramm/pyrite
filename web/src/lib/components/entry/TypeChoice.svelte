<script lang="ts">
	/**
	 * The entry-type picker for the New-entry and Clip forms (#392).
	 *
	 * When the KB declares types (`declared` non-empty), only those are
	 * offered and `value` defaults to one of them. The "use a type this KB
	 * does not declare" toggle is the ONLY thing that reveals the rest and
	 * sets `allowUndeclared: true` on `onchange` -- the caller (the page)
	 * passes that straight through as the `allow_undeclared` flag it sends,
	 * never defaulting it itself (#378 refusal is per-request).
	 *
	 * When the KB declares nothing (`declared` empty), every type is offered,
	 * there is no toggle, and `allowUndeclared` is always false: the flag is
	 * never sent because there is no undeclared vocabulary to opt out of.
	 */
	interface Props {
		types: string[];
		declared: string[];
		value: string;
		onchange: (choice: { entryType: string; allowUndeclared: boolean }) => void;
	}

	let { types, declared, value, onchange }: Props = $props();

	let overrideEnabled = $state(false);

	const hasDeclared = $derived(declared.length > 0);
	const offeredTypes = $derived(hasDeclared && !overrideEnabled ? declared : types);

	function selectType(newType: string) {
		onchange({ entryType: newType, allowUndeclared: hasDeclared && overrideEnabled });
	}

	function toggleOverride() {
		overrideEnabled = !overrideEnabled;
		// Snap the current value back into the now-offered set so the page
		// never holds a selection the visible options don't include.
		const nowOffered = hasDeclared && !overrideEnabled ? declared : types;
		if (!nowOffered.includes(value) && nowOffered.length > 0) {
			selectType(nowOffered[0]);
		} else {
			// Value is still valid; only allowUndeclared changed.
			onchange({ entryType: value, allowUndeclared: hasDeclared && overrideEnabled });
		}
	}
</script>

<div>
	<label for="entry-type-select" class="mb-1 block text-sm font-medium">Entry Type</label>
	<select
		id="entry-type-select"
		data-testid="entry-type-select"
		{value}
		onchange={(e) => selectType(e.currentTarget.value)}
		class="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
	>
		{#each offeredTypes as typeName (typeName)}
			<option value={typeName}>{typeName}</option>
		{/each}
	</select>

	{#if hasDeclared}
		<button
			type="button"
			data-testid="allow-undeclared-toggle"
			onclick={toggleOverride}
			class="mt-1 text-xs text-blue-600 hover:underline dark:text-blue-400"
		>
			{overrideEnabled
				? 'Only show this KB\'s declared types'
				: 'Use a type this KB does not declare'}
		</button>
	{/if}
</div>
