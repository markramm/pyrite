<!--
  Review queue ("For Amy"): a focused landing page listing drafts flagged for
  editorial review. The automation pipeline tags drafts ready for review (default
  tag: for-amy) in the drafts KB; this page surfaces exactly those, so the editor
  picks from a list instead of being sent per-draft URLs.

  Both the KB and the tag are overridable via ?kb=…&tag=… so the same page can
  serve other reviewers/queues later.
-->
<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import EntryList from '$lib/components/entry/EntryList.svelte';
	import { entryStore } from '$lib/stores/entries.svelte';
	import { page } from '$app/stores';

	const DEFAULT_KB = 'drafts';
	const DEFAULT_TAG = 'for-amy';

	const kb = $derived($page.url.searchParams.get('kb') ?? DEFAULT_KB);
	const tag = $derived($page.url.searchParams.get('tag') ?? DEFAULT_TAG);

	$effect(() => {
		entryStore.loadList({ kb, tag });
	});
</script>

<svelte:head><title>Review queue — Pyrite</title></svelte:head>

<Topbar breadcrumbs={[{ label: 'Review queue' }]} />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mb-1 flex items-center justify-between">
		<h1 class="text-2xl font-bold">Review queue</h1>
		<span
			class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
		>
			{kb} · #{tag}
		</span>
	</div>
	<p class="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
		Drafts flagged for review. Open one to copyedit and leave comments, then use
		<span class="font-medium">Submit for review</span> when you're done.
	</p>

	<EntryList {kb} />
</div>
