<script lang="ts">
	import Fuse from 'fuse.js';
	import { registerShortcut, formatShortcut } from '$lib/utils/keyboard';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { onMount } from 'svelte';

	export interface PaletteAction {
		id: string;
		label: string;
		shortcut?: string;
		action: () => void;
	}

	let open = $state(false);
	let query = $state('');
	let selectedIndex = $state(0);
	let inputEl = $state<HTMLInputElement | null>(null);

	const builtinActions: PaletteAction[] = [
		{
			id: 'new-entry',
			label: 'New Entry',
			shortcut: undefined,
			action: () => {
				window.location.href = '/entries/new';
			}
		},
		{
			id: 'search',
			label: 'Search Entries',
			shortcut: formatShortcut('o', ['mod']),
			action: () => {
				window.dispatchEvent(
					new KeyboardEvent('keydown', {
						key: 'o',
						ctrlKey: true,
						bubbles: true
					})
				);
			}
		},
		{
			id: 'toggle-theme',
			label: 'Toggle Theme',
			shortcut: undefined,
			action: () => {
				uiStore.toggleTheme();
			}
		}
	];

	let { actions = [] }: { actions?: PaletteAction[] } = $props();

	let allActions = $derived([...builtinActions, ...actions]);

	let fuse = $derived(
		new Fuse(allActions, {
			keys: ['label'],
			threshold: 0.4
		})
	);

	let filteredActions = $derived.by(() => {
		if (!query.trim()) return allActions;
		return fuse.search(query).map((r) => r.item);
	});

	function show() {
		open = true;
		query = '';
		selectedIndex = 0;
		setTimeout(() => inputEl?.focus(), 10);
	}

	function hide() {
		open = false;
		query = '';
	}

	function executeAction(action: PaletteAction) {
		hide();
		action.action();
	}

	function onInput(e: Event) {
		const target = e.target as HTMLInputElement;
		query = target.value;
		selectedIndex = 0;
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			selectedIndex = Math.min(selectedIndex + 1, filteredActions.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			selectedIndex = Math.max(selectedIndex - 1, 0);
		} else if (e.key === 'Enter' && filteredActions.length > 0) {
			e.preventDefault();
			executeAction(filteredActions[selectedIndex]);
		} else if (e.key === 'Escape') {
			e.preventDefault();
			hide();
		}
	}

	function onBackdropClick(e: MouseEvent) {
		if ((e.target as HTMLElement).dataset.backdrop) {
			hide();
		}
	}

	onMount(() => {
		const unsub = registerShortcut('k', ['mod'], () => {
			if (open) {
				hide();
			} else {
				show();
			}
		});
		return unsub;
	});
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-[15vh]"
		data-backdrop="true"
		data-testid="command-palette-backdrop"
		onkeydown={onKeydown}
		onclick={onBackdropClick}
	>
		<div class="w-full max-w-xl rounded-xl bg-white shadow-2xl dark:bg-zinc-900">
			<div class="flex items-center border-b border-zinc-200 px-4 dark:border-zinc-700">
				<svg class="mr-3 h-5 w-5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
				</svg>
				<input
					bind:this={inputEl}
					type="text"
					value={query}
					oninput={onInput}
					placeholder="Type a command..."
					class="w-full bg-transparent py-4 text-lg text-zinc-900 outline-none placeholder:text-zinc-400 dark:text-zinc-100"
					data-testid="command-palette-input"
				/>
				<kbd class="ml-2 hidden rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500 sm:inline dark:bg-zinc-800 dark:text-zinc-400">Esc</kbd>
			</div>

			{#if filteredActions.length > 0}
				<ul class="max-h-80 overflow-y-auto py-2" role="listbox" data-testid="command-palette-results">
					{#each filteredActions as action, i (action.id)}
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<li
							role="option"
							aria-selected={i === selectedIndex}
							class="flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm transition-colors {i === selectedIndex ? 'bg-blue-50 text-blue-900 dark:bg-blue-900/30 dark:text-blue-200' : 'text-zinc-700 hover:bg-zinc-50 dark:text-zinc-300 dark:hover:bg-zinc-800'}"
							onclick={() => executeAction(action)}
							onmouseenter={() => (selectedIndex = i)}
							data-testid="command-palette-action"
						>
							<span class="truncate font-medium">{action.label}</span>
							{#if action.shortcut}
								<kbd class="ml-auto shrink-0 rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">{action.shortcut}</kbd>
							{/if}
						</li>
					{/each}
				</ul>
			{:else}
				<div class="px-4 py-3 text-sm text-zinc-500" data-testid="command-palette-empty">No matching commands</div>
			{/if}

			<div class="flex items-center gap-4 border-t border-zinc-200 px-4 py-2 text-xs text-zinc-400 dark:border-zinc-700">
				<span><kbd class="rounded bg-zinc-100 px-1 dark:bg-zinc-800">↑↓</kbd> navigate</span>
				<span><kbd class="rounded bg-zinc-100 px-1 dark:bg-zinc-800">↵</kbd> run</span>
				<span><kbd class="rounded bg-zinc-100 px-1 dark:bg-zinc-800">esc</kbd> close</span>
			</div>
		</div>
	</div>
{/if}
