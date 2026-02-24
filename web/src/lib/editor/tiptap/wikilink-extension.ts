/**
 * Custom Tiptap node for wikilinks: [[entry-id|display text]]
 *
 * Renders as inline styled pills matching the CodeMirror wikilink style.
 */

import { Node, mergeAttributes } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

export interface WikilinkOptions {
	onSearch?: (query: string) => Promise<Array<{ id: string; title: string }>>;
}

declare module '@tiptap/core' {
	interface Commands<ReturnType> {
		wikilink: {
			insertWikilink: (target: string, display?: string) => ReturnType;
		};
	}
}

export const Wikilink = Node.create<WikilinkOptions>({
	name: 'wikilink',
	group: 'inline',
	inline: true,
	atom: true,

	addAttributes() {
		return {
			target: { default: '' },
			display: { default: '' }
		};
	},

	parseHTML() {
		return [
			{
				tag: 'span[data-wikilink]',
				getAttrs(dom) {
					const el = dom as HTMLElement;
					return {
						target: el.dataset.wikilink || '',
						display: el.textContent || ''
					};
				}
			}
		];
	},

	renderHTML({ node, HTMLAttributes }) {
		const target = node.attrs.target as string;
		const display = (node.attrs.display as string) || target;
		return [
			'span',
			mergeAttributes(HTMLAttributes, {
				'data-wikilink': target,
				class: 'wikilink',
				style:
					'background: rgba(59,130,246,0.15); color: #60a5fa; padding: 1px 6px; border-radius: 4px; cursor: pointer; font-size: 0.9em;'
			}),
			display
		];
	},

	addCommands() {
		return {
			insertWikilink:
				(target: string, display?: string) =>
				({ chain }) => {
					return chain()
						.insertContent({
							type: this.name,
							attrs: { target, display: display || target }
						})
						.run();
				}
		};
	},

	addProseMirrorPlugins() {
		return [
			new Plugin({
				key: new PluginKey('wikilink-click'),
				props: {
					handleClick(view, _pos, event) {
						const target = (event.target as HTMLElement).closest('[data-wikilink]');
						if (target) {
							const id = (target as HTMLElement).dataset.wikilink;
							if (id) {
								window.location.href = `/entries/${encodeURIComponent(id)}`;
								return true;
							}
						}
						return false;
					}
				}
			}),
			// Input rule: trigger autocomplete on [[
			new Plugin({
				key: new PluginKey('wikilink-input'),
				props: {
					decorations(state) {
						// Find `[[` patterns being typed and highlight them
						const { doc, selection } = state;
						const { from } = selection;
						const text = doc.textBetween(Math.max(0, from - 50), from);
						const match = text.match(/\[\[([^\]]*?)$/);
						if (match) {
							const start = from - match[0].length;
							return DecorationSet.create(doc, [
								Decoration.inline(start, from, {
									class: 'wikilink-input',
									style: 'color: #60a5fa;'
								})
							]);
						}
						return DecorationSet.empty;
					}
				}
			})
		];
	}
});
