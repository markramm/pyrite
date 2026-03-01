<script lang="ts">
	import { fly } from 'svelte/transition';

	interface Props {
		open: boolean;
		onclose: () => void;
	}

	let { open, onclose }: Props = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.preventDefault();
			onclose();
		}
	}

	function handleBackdropClick(e: MouseEvent) {
		if ((e.target as HTMLElement).dataset.backdrop) {
			onclose();
		}
	}

	const sections = [
		{
			title: 'Navigation',
			shortcuts: [
				{ keys: ['⌘', 'D'], description: 'Go to Daily Notes' },
				{ keys: ['⌘', '/'], description: 'Toggle sidebar' }
			]
		},
		{
			title: 'Search & Commands',
			shortcuts: [
				{ keys: ['⌘', 'K'], description: 'Command palette' },
				{ keys: ['⌘', 'O'], description: 'Quick search' }
			]
		},
		{
			title: 'Entry Editing',
			shortcuts: [
				{ keys: ['⌘', 'S'], description: 'Save entry' },
				{ keys: ['⌘', '⇧', 'B'], description: 'Toggle backlinks' },
				{ keys: ['⌘', '⇧', 'O'], description: 'Toggle outline' },
				{ keys: ['⌘', '⇧', 'G'], description: 'Toggle local graph' },
				{ keys: ['⌘', '⇧', 'H'], description: 'Toggle version history' }
			]
		},
		{
			title: 'AI',
			shortcuts: [{ keys: ['⌘', '⇧', 'K'], description: 'Toggle AI chat' }]
		}
	];
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
		data-backdrop="true"
		onclick={handleBackdropClick}
		in:fly={{ y: -8, duration: 180 }}
		out:fly={{ y: -8, duration: 120 }}
	>
		<div
			class="w-full max-w-lg rounded-xl border border-zinc-700 bg-zinc-900 shadow-2xl"
			role="dialog"
			aria-modal="true"
			aria-label="Keyboard shortcuts"
		>
			<!-- Header -->
			<div class="flex items-center justify-between border-b border-zinc-700 px-6 py-4">
				<h2 class="text-base font-semibold text-zinc-100">Keyboard Shortcuts</h2>
				<button
					onclick={onclose}
					class="rounded-md p-1 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100"
					aria-label="Close keyboard shortcuts"
				>
					<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Sections -->
			<div class="max-h-[70vh] overflow-y-auto px-6 py-4">
				<div class="space-y-6">
					{#each sections as section}
						<div>
							<h3 class="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
								{section.title}
							</h3>
							<div class="space-y-1">
								{#each section.shortcuts as shortcut}
									<div class="flex items-center justify-between rounded-md px-2 py-1.5 hover:bg-zinc-800/50">
										<span class="text-sm text-zinc-300">{shortcut.description}</span>
										<div class="flex items-center gap-1">
											{#each shortcut.keys as key}
												<kbd class="rounded bg-zinc-700 px-1.5 py-0.5 font-mono text-xs text-zinc-200">
													{key}
												</kbd>
											{/each}
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			</div>

			<!-- Footer -->
			<div class="border-t border-zinc-700 px-6 py-3">
				<p class="text-xs text-zinc-500">
					Press <kbd class="rounded bg-zinc-700 px-1.5 py-0.5 font-mono text-xs text-zinc-300">?</kbd> to toggle this overlay
				</p>
			</div>
		</div>
	</div>
{/if}
