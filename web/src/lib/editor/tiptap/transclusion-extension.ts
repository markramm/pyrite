/**
 * Custom Tiptap node for transclusions: ![[entry-id#heading]] and ![[entry-id^block-id]]
 *
 * Renders as block-level embedded cards with lazy-loaded content.
 */

import { Node, mergeAttributes } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { wsClient } from '$lib/api/websocket';
import {
	isCircularTransclusion,
	markTransclusionActive,
	CIRCULAR_REF_MESSAGE
} from '$lib/editor/transclusion-utils';

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
					// Subscribe to WebSocket updates to refresh transclusions
					const unsubscribeWs = wsClient.onEvent((event) => {
						if (event.type !== 'entry_updated') return;
						const embeds = document.querySelectorAll(
							`.transclusion-embed[data-transclusion="${event.entry_id}"]`
						);
						embeds.forEach((embed) => {
							const contentEl = embed.querySelector('.transclusion-content') as HTMLElement;
							if (!contentEl) return;
							// Reset to trigger reload on next update cycle
							contentEl.textContent = 'Loading...';
							delete contentEl.dataset.loaded;
						});
					});

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

								// Cycle detection
								if (isCircularTransclusion(target)) {
									htmlNode.textContent = CIRCULAR_REF_MESSAGE;
									htmlNode.dataset.loaded = 'true';
									return;
								}

								htmlNode.dataset.loaded = 'true';
								const cleanup = markTransclusionActive(target);
								try {
									const { api } = await import('$lib/api/client');
									const res = await api.resolveEntry(target);
									if (res.resolved && res.entry) {
										// Collection transclusion: render compact entry list
										if (res.entry.entry_type === 'collection') {
											const collectionId = res.entry.id;
											const kb = res.entry.kb_name;
											const collTitle = res.entry.title;

											// Update label to collection indicator
											const labelEl = el.querySelector('p');
											if (labelEl && labelEl.textContent?.startsWith('\u{1F4CE}')) {
												labelEl.textContent = `\u{1F4C2} ${collTitle}`;
											}

											try {
												const collRes = await api.getCollectionEntries(collectionId, kb, { limit: 10 });
												htmlNode.textContent = '';

												if (collRes.entries.length === 0) {
													htmlNode.textContent = 'Empty collection';
													htmlNode.style.color = '#9ca3af';
													htmlNode.style.fontStyle = 'italic';
													return;
												}

												// Compact list of entry titles
												const list = document.createElement('ul');
												list.style.cssText = 'margin: 0; padding: 0 0 0 1.2rem; list-style: disc;';
												for (const entry of collRes.entries) {
													const li = document.createElement('li');
													li.style.cssText = 'margin: 0.15rem 0;';
													const link = document.createElement('a');
													link.href = `/entries/${encodeURIComponent(entry.id)}`;
													link.textContent = entry.title;
													link.style.cssText = 'color: #3b82f6; text-decoration: none;';
													link.addEventListener('mouseenter', () => { link.style.textDecoration = 'underline'; });
													link.addEventListener('mouseleave', () => { link.style.textDecoration = 'none'; });
													link.addEventListener('click', (e) => {
														e.preventDefault();
														window.location.href = link.href;
													});
													li.appendChild(link);
													list.appendChild(li);
												}
												htmlNode.appendChild(list);

												// Count and "View all" link
												const footer = document.createElement('div');
												footer.style.cssText = 'margin-top: 0.4rem; font-size: 0.85em; color: #9ca3af;';
												const countText = collRes.total > collRes.entries.length
													? `Showing ${collRes.entries.length} of ${collRes.total} entries. `
													: `${collRes.total} ${collRes.total === 1 ? 'entry' : 'entries'}`;
												footer.textContent = countText;

												if (collRes.total > collRes.entries.length) {
													const viewAll = document.createElement('a');
													viewAll.href = `/collections/${encodeURIComponent(collectionId)}?kb=${encodeURIComponent(kb)}`;
													viewAll.textContent = 'View all \u2192';
													viewAll.style.cssText = 'color: #3b82f6; text-decoration: none;';
													viewAll.addEventListener('click', (e) => {
														e.preventDefault();
														window.location.href = viewAll.href;
													});
													footer.appendChild(viewAll);
												}
												htmlNode.appendChild(footer);
											} catch {
												htmlNode.textContent = '\u26A0 Failed to load collection entries';
											}
											return;
										}

										// Extract relevant section
										const heading = el.dataset.transclusionHeading;
										const blockId = el.dataset.transclusionBlock;
										let content: string;

										if (blockId) {
											// Fetch specific block by ID
											const blocksRes = await api.getEntryBlocks(
												res.entry.id,
												res.entry.kb_name,
												{ block_id: blockId }
											);
											const matchingBlock = blocksRes.blocks?.find(
												(b) => b.block_id === blockId
											);
											if (matchingBlock) {
												content = matchingBlock.content;
											} else {
												// Fallback to full body if block not found
												const entryRes = await api.getEntry(res.entry.id, {
													kb: res.entry.kb_name
												});
												content = entryRes.body || '';
											}
										} else {
											const entryRes = await api.getEntry(res.entry.id, {
												kb: res.entry.kb_name
											});
											content = entryRes.body || '';
											if (heading) {
												const headingRegex = new RegExp(
													`^##?#?#?#?#?\\s+${heading.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*$`,
													'mi'
												);
												const match = headingRegex.exec(content);
												if (match) {
													const start = match.index + match[0].length;
													const nextHeading = content
														.slice(start)
														.search(/^##?#?#?#?#?\s+/m);
													content =
														nextHeading === -1
															? content.slice(start).trim()
															: content
																	.slice(start, start + nextHeading)
																	.trim();
												}
											}
										}
										htmlNode.textContent =
											content.slice(0, 500) + (content.length > 500 ? '...' : '');
									} else {
										htmlNode.textContent = '\u26A0 Entry not found';
									}
								} catch {
									htmlNode.textContent = '\u26A0 Failed to load';
								} finally {
									cleanup();
								}
							});
						},
						destroy() {
							unsubscribeWs();
						}
					};
				}
			})
		];
	}
});
