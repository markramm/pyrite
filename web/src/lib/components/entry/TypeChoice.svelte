<script lang="ts">
	/**
	 * The entry-type picker for the New-entry and Clip forms (#392).
	 *
	 * When the KB declares types (`declared` non-empty), only those are
	 * offered. With more than one declared type, nothing is preselected: the
	 * user must choose explicitly (round-1 cold read blocker 2 -- an
	 * alphabetical default is still an arbitrary one). `value` starts `''`
	 * and the caller (the page) keeps its own `entryType` at `''` -- and its
	 * submit button disabled -- until `onchange` reports a real type. With
	 * exactly one declared type there is nothing to choose, so it is
	 * auto-selected on mount.
	 *
	 * The "use a type this KB does not declare" toggle is the ONLY thing that
	 * reveals the rest and sets `allowUndeclared: true` on `onchange` -- the
	 * caller passes that straight through as the `allow_undeclared` flag it
	 * sends, never defaulting it itself (#378 refusal is per-request).
	 * `forceOverride` starts the toggle engaged and `value` preselected to a
	 * type the KB does not declare: the New-entry form uses this for a
	 * template that named an undeclared type, so the user SEES that choice
	 * and can back out of it, rather than the page silently sending the flag.
	 *
	 * When the KB declares nothing (`declared` empty), every type is offered,
	 * there is no toggle, and `allowUndeclared` is always false.
	 */
	interface Props {
		types: string[];
		declared: string[];
		value: string;
		onchange: (choice: { entryType: string; allowUndeclared: boolean }) => void;
		id?: string;
		forceOverride?: boolean;
		typeDescriptions?: Record<string, string>;
	}

	let {
		types,
		declared,
		value,
		onchange,
		id = 'entry-type-select',
		forceOverride = false,
		typeDescriptions = {}
	}: Props = $props();

	// Seeded once from the prop at mount; `forceOverride` is a one-shot
	// instruction ("start with the override engaged"), not a live binding --
	// wrapped to avoid the "referenced locally" warning for that pattern.
	let overrideEnabled = $state((() => forceOverride)());

	const hasDeclared = $derived(declared.length > 0);
	const singleDeclared = $derived(hasDeclared && declared.length === 1 ? declared[0] : null);
	const offeredTypes = $derived(hasDeclared && !overrideEnabled ? declared : types);
	// A placeholder is needed only when there is a real choice to make: more
	// than one declared type, nothing chosen yet, and the override is not
	// forcing a specific (undeclared) value into view.
	const needsPlaceholder = $derived(
		hasDeclared && !overrideEnabled && declared.length > 1 && !value
	);

	$effect(() => {
		// Exactly one declared type: nothing to choose, so report it once.
		if (singleDeclared && value !== singleDeclared && !forceOverride) {
			onchange({ entryType: singleDeclared, allowUndeclared: false });
		}
	});

	function selectType(newType: string) {
		if (!newType) return;
		onchange({ entryType: newType, allowUndeclared: hasDeclared && overrideEnabled });
	}

	function toggleOverride() {
		overrideEnabled = !overrideEnabled;
		// Snap the current value back into the now-offered set so the page
		// never holds a selection the visible options don't include.
		const nowOffered = hasDeclared && !overrideEnabled ? declared : types;
		if (!nowOffered.includes(value) && nowOffered.length > 0) {
			// Only one declared type left to snap back to -- pick it. Otherwise
			// (declared.length > 1) go back to unchosen rather than guess.
			if (!overrideEnabled && nowOffered.length === 1) {
				selectType(nowOffered[0]);
			} else if (!overrideEnabled) {
				onchange({ entryType: '', allowUndeclared: false });
			} else {
				selectType(nowOffered[0]);
			}
		} else {
			// Value is still valid; only allowUndeclared changed.
			onchange({ entryType: value, allowUndeclared: hasDeclared && overrideEnabled });
		}
	}

	function describe(typeName: string): string {
		const d = typeDescriptions[typeName];
		return d ? `${typeName} — ${d}` : typeName;
	}
</script>

<div>
	<label for={id} class="mb-1 block text-sm font-medium">Entry Type</label>
	<select
		{id}
		data-testid="entry-type-select"
		value={needsPlaceholder ? '' : value}
		onchange={(e) => selectType(e.currentTarget.value)}
		class="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
	>
		{#if needsPlaceholder}
			<option value="" disabled selected>Choose a type…</option>
		{/if}
		{#each offeredTypes as typeName (typeName)}
			<option value={typeName}>{describe(typeName)}</option>
		{/each}
	</select>

	{#if hasDeclared}
		<button
			type="button"
			data-testid="allow-undeclared-toggle"
			aria-pressed={overrideEnabled}
			onclick={toggleOverride}
			class="mt-1 text-xs text-blue-600 hover:underline dark:text-blue-400"
		>
			{overrideEnabled
				? 'Only show this KB\'s declared types'
				: 'Use a type this KB does not declare'}
		</button>
	{/if}
</div>
