<script lang="ts">
	import { EditorState } from '@codemirror/state';
	import { EditorView } from '@codemirror/view';
	import { onMount } from 'svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { createEditorExtensions, themeCompartment } from './codemirror/setup';
	import { darkTheme, lightTheme } from './codemirror/theme';

	interface Props {
		content: string;
		onchange?: (content: string) => void;
		onsave?: () => void;
		readonly?: boolean;
	}

	let { content, onchange, onsave, readonly = false }: Props = $props();

	let editorContainer: HTMLDivElement;
	let view = $state<EditorView | undefined>();

	function createView(doc: string) {
		if (view) view.destroy();

		const isDark = typeof document !== 'undefined'
			? document.documentElement.classList.contains('dark')
			: uiStore.theme === 'dark';
		const extensions = createEditorExtensions({
			dark: isDark,
			onSave: onsave,
			onChange: onchange
		});

		if (readonly) {
			extensions.push(EditorState.readOnly.of(true));
		}

		const state = EditorState.create({ doc, extensions });
		view = new EditorView({ state, parent: editorContainer });
	}

	onMount(() => {
		return () => view?.destroy();
	});

	// Initialize or update editor when content or container changes
	$effect(() => {
		if (!editorContainer) return;
		if (!view) {
			// First render — create the editor with current content
			createView(content);
		} else if (content !== view.state.doc.toString()) {
			// Content changed from outside — update editor
			view.dispatch({
				changes: { from: 0, to: view.state.doc.length, insert: content }
			});
		}
	});

	// Swap theme dynamically when light/dark mode changes
	$effect(() => {
		// Read uiStore.theme to create a reactive dependency
		const _theme = uiStore.theme;
		// But check the actual DOM class for the ground truth (handles localStorage hydration race)
		if (view && typeof document !== 'undefined') {
			const isDark = document.documentElement.classList.contains('dark');
			view.dispatch({
				effects: themeCompartment.reconfigure(isDark ? darkTheme : lightTheme)
			});
		}
	});

	export function getContent(): string {
		return view?.state.doc.toString() ?? content;
	}

	export function focus() {
		view?.focus();
	}
</script>

<div bind:this={editorContainer} class="h-full w-full overflow-auto"></div>
