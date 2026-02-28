/**
 * Custom Tiptap node for transclusions: ![[entry-id#heading]] and ![[entry-id^block-id]]
 *
 * Renders as block-level embedded cards with lazy-loaded content.
 */

import { Node, mergeAttributes } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';

export const Transclusion = Node.create({
	name: 'transclusion',
	group: 'block',
	atom: true,

	addAttributes() {
		return {
			target: { default: '' },
			heading: { default: null },
			blockId: { default: null },
			kb: { default: null }
		};
	},

	parseHTML() {
		return [
			{
				tag: 'div[data-transclusion]',
				getAttrs(dom) {
					const el = dom as HTMLElement;
					return {
						target: el.dataset.transclusion || '',
						heading: el.dataset.transclusionHeading || null,
						blockId: el.dataset.transclusionBlock || null,
						kb: el.dataset.transclusionKb || null
					};
				}
			}
		];
	},

	renderHTML({ node, HTMLAttributes }) {
		const target = node.attrs.target as string;
		const heading = node.attrs.heading as string | null;
		const blockId = node.attrs.blockId as string | null;
		const label = heading
			? `${target} \u00A7 ${heading}`
			: blockId
				? `${target} ^${blockId}`
				: target;
		return [
			'div',
			mergeAttributes(HTMLAttributes, {
				'data-transclusion': target,
				'data-transclusion-heading': heading || '',
				'data-transclusion-block': blockId || '',
				class: 'transclusion-embed',
				style:
					'border: 1px solid #374151; border-left: 3px solid #3b82f6; padding: 0.75rem; margin: 0.5rem 0; border-radius: 4px; background: rgba(59,130,246,0.05);'
			}),
			[
				'p',
				{ style: 'margin: 0 0 0.5rem 0; color: #9ca3af; font-size: 0.85em;' },
				`\u{1F4CE} ${label}`
			],
			['p', { class: 'transclusion-content', style: 'margin: 0;' }, 'Loading...']
		];
	},

	addProseMirrorPlugins() {
		return [
			new Plugin({
				key: new PluginKey('transclusion-loader'),
				view() {
					return {
						update(view) {
							const nodes = view.dom.querySelectorAll(
								'.transclusion-embed .transclusion-content'
							);
							nodes.forEach(async (node) => {
								const el = node.closest('[data-transclusion]') as HTMLElement;
								if (!el) return;
								const htmlNode = node as HTMLElement;
								if (htmlNode.dataset.loaded || htmlNode.textContent !== 'Loading...')
									return;
								const target = el.dataset.transclusion;
								if (!target) return;
								htmlNode.dataset.loaded = 'true';
								try {
									const { api } = await import('$lib/api/client');
									const res = await api.resolveEntry(target);
									if (res.resolved && res.entry) {
										const entryRes = await api.getEntry(res.entry.id, {
											kb: res.entry.kb_name
										});
										const body = entryRes.body || '';
										// Extract relevant section
										const heading = el.dataset.transclusionHeading;
										const blockId = el.dataset.transclusionBlock;
										let content = body;
										if (heading) {
											const headingRegex = new RegExp(
												`^##?#?#?#?#?\\s+${heading.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*$`,
												'mi'
											);
											const match = headingRegex.exec(body);
											if (match) {
												const start = match.index + match[0].length;
												const nextHeading = body
													.slice(start)
													.search(/^##?#?#?#?#?\s+/m);
												content =
													nextHeading === -1
														? body.slice(start).trim()
														: body.slice(start, start + nextHeading).trim();
											}
										}
										htmlNode.textContent =
											content.slice(0, 500) + (content.length > 500 ? '...' : '');
									} else {
										htmlNode.textContent = '\u26A0 Entry not found';
									}
								} catch {
									htmlNode.textContent = '\u26A0 Failed to load';
								}
							});
						}
					};
				}
			})
		];
	}
});
