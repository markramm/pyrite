<script lang="ts">
	import { Editor } from '@tiptap/core';
	import StarterKit from '@tiptap/starter-kit';
	import Link from '@tiptap/extension-link';
	import Placeholder from '@tiptap/extension-placeholder';
	import TaskList from '@tiptap/extension-task-list';
	import TaskItem from '@tiptap/extension-task-item';
	import { Wikilink } from './tiptap/wikilink-extension';
	import { markdownToHtml, htmlToMarkdown } from './tiptap/markdown';
	import { onMount } from 'svelte';

	interface Props {
		content: string;
		onchange?: (content: string) => void;
		onsave?: () => void;
		readonly?: boolean;
	}

	let { content, onchange, onsave, readonly = false }: Props = $props();

	let editorContainer: HTMLDivElement;
	let editor: Editor | undefined;

	onMount(() => {
		editor = new Editor({
			element: editorContainer,
			editable: !readonly,
			content: markdownToHtml(content),
			extensions: [
				StarterKit.configure({
					heading: { levels: [1, 2, 3, 4, 5, 6] }
				}),
				Link.configure({
					openOnClick: true,
					HTMLAttributes: { class: 'text-blue-500 underline' }
				}),
				Placeholder.configure({
					placeholder: 'Start writing...'
				}),
				TaskList,
				TaskItem.configure({ nested: true }),
				Wikilink
			],
			onUpdate: ({ editor: ed }) => {
				const html = ed.getHTML();
				const md = htmlToMarkdown(html);
				onchange?.(md);
			},
			editorProps: {
				attributes: {
					class: 'prose dark:prose-invert max-w-none outline-none min-h-[300px] p-4'
				},
				handleKeyDown(_view, event) {
					if ((event.metaKey || event.ctrlKey) && event.key === 's') {
						event.preventDefault();
						onsave?.();
						return true;
					}
					return false;
				}
			}
		});

		return () => editor?.destroy();
	});

	// Update content from outside
	$effect(() => {
		if (editor) {
			const currentMd = htmlToMarkdown(editor.getHTML());
			if (content !== currentMd) {
				editor.commands.setContent(markdownToHtml(content));
			}
		}
	});

	export function getContent(): string {
		if (!editor) return content;
		return htmlToMarkdown(editor.getHTML());
	}

	export function focus() {
		editor?.commands.focus();
	}
</script>

<div class="tiptap-editor h-full w-full overflow-auto">
	<div bind:this={editorContainer} class="h-full"></div>
</div>

<style>
	.tiptap-editor :global(.ProseMirror) {
		outline: none;
		min-height: 300px;
	}
	.tiptap-editor :global(.ProseMirror p.is-editor-empty:first-child::before) {
		color: #6b7280;
		content: attr(data-placeholder);
		float: left;
		height: 0;
		pointer-events: none;
	}
	.tiptap-editor :global(ul[data-type='taskList']) {
		list-style: none;
		padding: 0;
	}
	.tiptap-editor :global(ul[data-type='taskList'] li) {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
	}
	.tiptap-editor :global(ul[data-type='taskList'] li label) {
		margin-top: 0.2rem;
	}
</style>
