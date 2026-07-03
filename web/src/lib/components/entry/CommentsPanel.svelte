<!--
  CommentsPanel: editor (e.g. Amy) review comments anchored to passages.

  Comments are stored in the entry's frontmatter under metadata.review_comments
  and ride the per-user git worktree → merge flow, so they land in the KB for
  the automation pipeline to consume. Anchoring is by quote + context (see
  comment-anchor.ts), never offsets, so comments survive prose edits.
-->
<script lang="ts">
	import type { ReviewComment } from '$lib/editor/comment-anchor';
	import { isOrphaned } from '$lib/editor/comment-anchor';

	interface Props {
		comments: ReviewComment[];
		body: string;
		author: string;
		canComment: boolean;
		/** Add a new comment from the current text selection. */
		onAdd: (note: string) => void;
		/** Toggle a comment between open/resolved. */
		onToggleStatus: (id: string) => void;
		/** Delete a comment. */
		onDelete: (id: string) => void;
		/** Scroll the rendered body to a comment's quote. */
		onJump: (comment: ReviewComment) => void;
	}

	let { comments, body, author, canComment, onAdd, onToggleStatus, onDelete, onJump }: Props =
		$props();

	let draft = $state('');

	const open = $derived(comments.filter((c) => c.status !== 'resolved'));
	const resolved = $derived(comments.filter((c) => c.status === 'resolved'));

	function submit() {
		const note = draft.trim();
		if (!note) return;
		onAdd(note);
		draft = '';
	}
</script>

<div class="flex h-full flex-col overflow-hidden">
	<div
		class="flex items-center justify-between border-b border-zinc-200 px-4 py-2 dark:border-zinc-800"
	>
		<h2 class="text-sm font-semibold text-zinc-600 dark:text-zinc-400">
			Comments ({open.length})
		</h2>
	</div>

	{#if canComment}
		<div class="border-b border-zinc-200 p-3 dark:border-zinc-800">
			<p class="mb-1.5 text-[11px] text-zinc-500 dark:text-zinc-400">
				Select text in the document, then write a note to anchor it there. Leave the selection
				empty for a general note.
			</p>
			<textarea
				bind:value={draft}
				rows="3"
				placeholder="Add a comment or suggestion…"
				class="w-full resize-y rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-900"
			></textarea>
			<div class="mt-1.5 flex justify-end">
				<button
					onclick={submit}
					disabled={!draft.trim()}
					class="rounded-md bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
				>
					Comment
				</button>
			</div>
		</div>
	{/if}

	<div class="flex-1 overflow-y-auto">
		{#if comments.length === 0}
			<div class="flex items-center justify-center p-6">
				<span class="text-sm text-zinc-400">No comments yet</span>
			</div>
		{:else}
			<ul class="divide-y divide-zinc-100 dark:divide-zinc-800/50">
				{#each [...open, ...resolved] as c (c.id)}
					{@const orphaned = c.status !== 'resolved' && c.quote && isOrphaned(body, c)}
					<li class="px-4 py-3 {c.status === 'resolved' ? 'opacity-60' : ''}">
						{#if c.quote}
							<button
								onclick={() => onJump(c)}
								disabled={!!orphaned}
								class="mb-1.5 block w-full truncate border-l-2 border-amber-400 bg-amber-50 px-2 py-1 text-left text-xs italic text-zinc-600 hover:bg-amber-100 disabled:cursor-default disabled:hover:bg-amber-50 dark:bg-amber-900/20 dark:text-zinc-300 dark:hover:bg-amber-900/30"
								title={orphaned ? 'Passage changed — comment no longer anchored' : 'Jump to passage'}
							>
								“{c.quote}”
							</button>
						{/if}
						{#if orphaned}
							<span
								class="mb-1 inline-flex items-center rounded-full bg-orange-100 px-1.5 py-0.5 text-[10px] font-medium text-orange-700 dark:bg-orange-900/40 dark:text-orange-300"
							>
								passage changed
							</span>
						{/if}
						<p class="whitespace-pre-wrap text-sm text-zinc-900 dark:text-zinc-100">{c.note}</p>
						<div class="mt-1.5 flex items-center gap-3 text-[11px] text-zinc-400">
							<span>{c.author}</span>
							<button class="hover:text-blue-600" onclick={() => onToggleStatus(c.id)}>
								{c.status === 'resolved' ? 'Reopen' : 'Resolve'}
							</button>
							<button class="hover:text-red-600" onclick={() => onDelete(c.id)}>Delete</button>
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>
