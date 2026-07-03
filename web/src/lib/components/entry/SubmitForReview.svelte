<!--
  SubmitForReview: editor-side control to submit worktree changes for admin review.

  When auth is on, a non-admin's edits land in their own git worktree/branch
  (handled server-side). This surfaces the existing /api/worktree/* endpoints so
  the editor can see how many changes are pending and submit them — closing the
  loop the merge-queue admin page already implements on the reviewer side.
-->
<script lang="ts">
	import { api } from '$lib/api/client';
	import { uiStore } from '$lib/stores/ui.svelte';

	interface Props {
		kb: string;
		/** Bump this to force a status refetch (e.g. after a save). */
		refreshKey?: unknown;
	}

	let { kb, refreshKey }: Props = $props();

	type Status = {
		has_worktree: boolean;
		status: string;
		changes_count: number;
		submitted_at: string | null;
		feedback: string | null;
		branch: string | null;
	};

	let status = $state<Status | null>(null);
	let submitting = $state(false);

	async function refresh() {
		try {
			status = await api.getWorktreeStatus(kb);
		} catch {
			status = null; // KB not under git, or not authenticated — render nothing.
		}
	}

	$effect(() => {
		// Re-run whenever kb or refreshKey changes.
		void kb;
		void refreshKey;
		refresh();
	});

	async function submit() {
		submitting = true;
		try {
			await api.submitWorktree(kb);
			uiStore.toast('Submitted for review', 'success');
			await refresh();
		} catch (e) {
			uiStore.toast(e instanceof Error ? e.message : 'Submit failed', 'error');
		} finally {
			submitting = false;
		}
	}

	const pending = $derived(status?.has_worktree && status.changes_count > 0);
	const isSubmitted = $derived(status?.status === 'submitted');
	const wasRejected = $derived(status?.status === 'rejected');
</script>

{#if status?.has_worktree}
	<div class="flex items-center gap-2">
		{#if isSubmitted}
			<span
				class="inline-flex items-center rounded-md bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
				title={status?.submitted_at ?? ''}
			>
				Awaiting review
			</span>
		{:else}
			{#if wasRejected && status?.feedback}
				<span
					class="hidden max-w-xs truncate text-xs text-red-600 dark:text-red-400 lg:inline"
					title={status.feedback}
				>
					Changes requested: {status.feedback}
				</span>
			{/if}
			<button
				onclick={submit}
				disabled={!pending || submitting}
				class="rounded-md border border-emerald-500 bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50 dark:bg-emerald-900/30 dark:text-emerald-300"
				title={pending ? 'Send your edits to the reviewer' : 'No changes to submit'}
			>
				{submitting
					? 'Submitting…'
					: pending
						? `Submit for review (${status?.changes_count})`
						: 'Submit for review'}
			</button>
		{/if}
	</div>
{/if}
