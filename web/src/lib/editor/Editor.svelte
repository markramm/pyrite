<script lang="ts">
	import { EditorState } from '@codemirror/state';
	import { EditorView } from '@codemirror/view';
	import { onMount } from 'svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { createEditorExtensions } from './codemirror/setup';

	interface Props {
		content: string;
		onchange?: (content: string) => void;
		onsave?: () => void;
		readonly?: boolean;
	}

	let { content, onchange, onsave, readonly = false }: Props = $props();

	let editorContainer: HTMLDivElement;
	let view: EditorView | undefined;

	function createView(doc: string) {
		if (view) view.destroy();

		const extensions = createEditorExtensions({
			dark: uiStore.theme === 'dark',
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
		createView(content);
		return () => view?.destroy();
	});

	// Update content from outside (e.g., loading a new entry)
	$effect(() => {
		if (view && content !== view.state.doc.toString()) {
			view.dispatch({
				changes: { from: 0, to: view.state.doc.length, insert: content }
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
