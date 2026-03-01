<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { onMount } from 'svelte';
	import {
		getQAStatus,
		getQAValidation,
		getQACoverage,
		type QAStatus,
		type QAIssue,
		type QAValidationKB,
		type QAValidationAll,
		type QACoverage
	} from '$lib/api/qa';

	let status = $state<QAStatus | null>(null);
	let issues = $state<QAIssue[]>([]);
	let coverage = $state<QACoverage | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	let selectedKb = $state('');
	let severityFilter = $state('');

	const severityColors: Record<string, string> = {
		error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
		warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
		info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
	};

	async function loadData() {
		loading = true;
		error = null;
		try {
			const kb = selectedKb || undefined;
			status = await getQAStatus(kb);

			const validation = await getQAValidation(kb);
			if ('kbs' in validation) {
				issues = (validation as QAValidationAll).kbs.flatMap((k) => k.issues);
			} else {
				issues = (validation as QAValidationKB).issues;
			}

			if (selectedKb) {
				coverage = await getQACoverage(selectedKb);
			} else {
				coverage = null;
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load QA data';
		} finally {
			loading = false;
		}
	}

	function handleKbChange() {
		loadData();
	}

	$effect(() => {
		// Re-run when selectedKb changes
		selectedKb;
		loadData();
	});

	let filteredIssues = $derived(
		severityFilter ? issues.filter((i) => i.severity === severityFilter) : issues
	);
</script>

<svelte:head>
	<title>QA Dashboard - Pyrite</title>
</svelte:head>

<div class="flex h-full flex-col">
	<Topbar title="QA Dashboard" />

	<div class="flex-1 overflow-y-auto p-6">
		<!-- Filters -->
		<div class="mb-6 flex items-center gap-4">
			<select
				bind:value={selectedKb}
				class="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
			>
				<option value="">All KBs</option>
				{#each kbStore.kbs as kb}
					<option value={kb.name}>{kb.name}</option>
				{/each}
			</select>

			<select
				bind:value={severityFilter}
				class="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
			>
				<option value="">All Severities</option>
				<option value="error">Error</option>
				<option value="warning">Warning</option>
				<option value="info">Info</option>
			</select>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<div class="text-zinc-500">Loading QA data...</div>
			</div>
		{:else if error}
			<div class="rounded-md bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
				{error}
			</div>
		{:else}
			<!-- Status Summary -->
			{#if status}
				<div class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
					<div
						class="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800"
					>
						<div class="text-sm text-zinc-500">Total Entries</div>
						<div class="text-2xl font-bold">{status.total_entries}</div>
					</div>
					<div
						class="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800"
					>
						<div class="text-sm text-zinc-500">Total Issues</div>
						<div class="text-2xl font-bold">{status.total_issues}</div>
					</div>
					{#each Object.entries(status.issues_by_severity) as [sev, count]}
						<div
							class="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800"
						>
							<div class="text-sm capitalize text-zinc-500">{sev}</div>
							<div class="text-2xl font-bold">{count}</div>
						</div>
					{/each}
				</div>
			{/if}

			<!-- Coverage Stats -->
			{#if coverage}
				<div class="mb-6">
					<h2 class="mb-3 text-lg font-semibold">Coverage</h2>
					<div class="grid grid-cols-2 gap-4 md:grid-cols-5">
						<div
							class="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800"
						>
							<div class="text-sm text-zinc-500">Total</div>
							<div class="text-xl font-bold">{coverage.total}</div>
						</div>
						<div
							class="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800"
						>
							<div class="text-sm text-zinc-500">Assessed</div>
							<div class="text-xl font-bold">{coverage.assessed}</div>
						</div>
						<div
							class="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800"
						>
							<div class="text-sm text-zinc-500">Unassessed</div>
							<div class="text-xl font-bold">{coverage.unassessed}</div>
						</div>
						<div
							class="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800"
						>
							<div class="text-sm text-zinc-500">Coverage</div>
							<div class="text-xl font-bold">{coverage.coverage_pct}%</div>
						</div>
						{#each Object.entries(coverage.by_status) as [st, cnt]}
							<div
								class="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800"
							>
								<div class="text-sm capitalize text-zinc-500">{st}</div>
								<div class="text-xl font-bold">{cnt}</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Issues List -->
			<div>
				<h2 class="mb-3 text-lg font-semibold">
					Issues ({filteredIssues.length})
				</h2>
				{#if filteredIssues.length === 0}
					<div class="rounded-md bg-green-50 p-4 text-green-700 dark:bg-green-900/20 dark:text-green-400">
						No issues found.
					</div>
				{:else}
					<div class="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-700">
						<table class="w-full text-left text-sm">
							<thead class="bg-zinc-50 dark:bg-zinc-800">
								<tr>
									<th class="px-4 py-3 font-medium">Severity</th>
									<th class="px-4 py-3 font-medium">Rule</th>
									<th class="px-4 py-3 font-medium">Entry</th>
									<th class="px-4 py-3 font-medium">KB</th>
									<th class="px-4 py-3 font-medium">Message</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-zinc-200 dark:divide-zinc-700">
								{#each filteredIssues as issue}
									<tr class="bg-white dark:bg-zinc-900">
										<td class="px-4 py-3">
											<span
												class="inline-block rounded-full px-2 py-0.5 text-xs font-medium {severityColors[
													issue.severity
												] || ''}"
											>
												{issue.severity}
											</span>
										</td>
										<td class="px-4 py-3 font-mono text-xs">{issue.rule}</td>
										<td class="px-4 py-3">
											<a
												href="/entries/{issue.entry_id}?kb={issue.kb_name}"
												class="text-blue-600 hover:underline dark:text-blue-400"
											>
												{issue.entry_id}
											</a>
										</td>
										<td class="px-4 py-3 text-zinc-500">{issue.kb_name}</td>
										<td class="px-4 py-3 text-zinc-600 dark:text-zinc-400"
											>{issue.message}</td
										>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
