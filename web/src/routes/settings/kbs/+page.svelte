<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { KBHealthResponse, KBReindexResponse, GitHubConnectionStatus } from '$lib/api/types';
	import { onMount } from 'svelte';

	let showAddDialog = $state(false);
	let addName = $state('');
	let addPath = $state('');
	let addType = $state('generic');
	let addDescription = $state('');
	let adding = $state(false);
	let addError = $state<string | null>(null);

	let reindexing = $state<string | null>(null);
	let reindexResult = $state<KBReindexResponse | null>(null);

	let healthResult = $state<KBHealthResponse | null>(null);
	let healthLoading = $state<string | null>(null);

	let confirmDelete = $state<string | null>(null);
	let deleting = $state(false);
	let deleteError = $state<string | null>(null);

	let feedback = $state<{ ok: boolean; message: string } | null>(null);

	// GitHub connection
	let ghStatus = $state<GitHubConnectionStatus | null>(null);
	let ghLoading = $state(false);
	let ghDisconnecting = $state(false);

	// Ephemeral KBs (admin only)
	type EphemeralKB = {
		name: string;
		path: string;
		created_at: number | null;
		ttl: number | null;
		expires_at: number | null;
		expired: boolean;
	};
	let ephemeralKBs = $state<EphemeralKB[]>([]);
	let ephemeralLoading = $state(false);
	let expiring = $state<string | null>(null);

	const isAdmin = $derived(authStore.isAdmin);

	onMount(() => {
		kbStore.load();
		loadGitHubStatus();
		if (isAdmin) {
			loadEphemeral();
		}
	});

	async function loadGitHubStatus() {
		ghLoading = true;
		try {
			ghStatus = await api.getGitHubConnectionStatus();
		} catch {
			// GitHub status not available — hide panel
		} finally {
			ghLoading = false;
		}
	}

	async function handleDisconnectGitHub() {
		ghDisconnecting = true;
		try {
			await api.disconnectGitHub();
			ghStatus = { connected: false, github_configured: true };
			feedback = { ok: true, message: 'GitHub disconnected' };
		} catch (e) {
			feedback = {
				ok: false,
				message: e instanceof ApiError ? e.detail : 'Failed to disconnect'
			};
		} finally {
			ghDisconnecting = false;
		}
	}

	async function loadEphemeral() {
		ephemeralLoading = true;
		try {
			const data = await api.listEphemeralKBs();
			ephemeralKBs = data.ephemeral_kbs;
		} catch {
			// Silently ignore — ephemeral section just won't show
		} finally {
			ephemeralLoading = false;
		}
	}

	async function handleForceExpire(name: string) {
		expiring = name;
		try {
			await api.forceExpireKB(name);
			ephemeralKBs = ephemeralKBs.filter((k) => k.name !== name);
			feedback = { ok: true, message: `Ephemeral KB '${name}' expired` };
			kbStore.load(); // Refresh main list
		} catch (e) {
			feedback = {
				ok: false,
				message: e instanceof ApiError ? e.detail : 'Failed to expire'
			};
		} finally {
			expiring = null;
		}
	}

	function openAddDialog() {
		addName = '';
		addPath = '';
		addType = 'generic';
		addDescription = '';
		addError = null;
		showAddDialog = true;
	}

	async function handleAdd() {
		if (!addName.trim() || !addPath.trim()) return;
		adding = true;
		addError = null;
		try {
			await kbStore.add({
				name: addName.trim(),
				path: addPath.trim(),
				kb_type: addType,
				description: addDescription.trim()
			});
			showAddDialog = false;
			feedback = { ok: true, message: `KB '${addName}' added successfully` };
		} catch (e) {
			addError = e instanceof ApiError ? e.detail : 'Failed to add KB';
		} finally {
			adding = false;
		}
	}

	async function handleReindex(name: string) {
		reindexing = name;
		reindexResult = null;
		try {
			const result = await kbStore.reindex(name);
			reindexResult = result;
			feedback = {
				ok: true,
				message: `Reindexed '${name}': +${result.added} added, ~${result.updated} updated, -${result.removed} removed`
			};
		} catch (e) {
			feedback = {
				ok: false,
				message: e instanceof ApiError ? e.detail : 'Reindex failed'
			};
		} finally {
			reindexing = null;
		}
	}

	async function handleHealth(name: string) {
		healthLoading = name;
		healthResult = null;
		try {
			healthResult = await kbStore.getHealth(name);
		} catch (e) {
			feedback = {
				ok: false,
				message: e instanceof ApiError ? e.detail : 'Health check failed'
			};
		} finally {
			healthLoading = null;
		}
	}

	async function handleDelete(name: string) {
		deleting = true;
		deleteError = null;
		try {
			await kbStore.remove(name);
			confirmDelete = null;
			feedback = { ok: true, message: `KB '${name}' removed` };
		} catch (e) {
			deleteError = e instanceof ApiError ? e.detail : 'Failed to remove KB';
		} finally {
			deleting = false;
		}
	}
</script>

<Topbar title="Knowledge Bases" />

<div class="p-6 max-w-5xl mx-auto">
	<div class="flex items-center justify-between mb-6">
		<div>
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Knowledge Bases</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
				Manage registered knowledge bases. Config-defined KBs are read-only.
			</p>
		</div>
		<button
			class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
			onclick={openAddDialog}
		>
			Add KB
		</button>
	</div>

	<!-- GitHub Connection Panel -->
	{#if ghStatus?.github_configured}
		<div class="mb-4 bg-white dark:bg-gray-800 rounded-lg shadow p-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<svg class="w-5 h-5 text-gray-700 dark:text-gray-300" viewBox="0 0 16 16" fill="currentColor">
						<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
					</svg>
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
							GitHub Connection
						</div>
						{#if ghStatus.connected}
							<div class="text-xs text-green-600 dark:text-green-400">
								Connected{ghStatus.username ? ` as @${ghStatus.username}` : ''}
							</div>
						{:else}
							<div class="text-xs text-gray-500 dark:text-gray-400">
								Connect GitHub for repo operations (fork, subscribe, export)
							</div>
						{/if}
					</div>
				</div>
				<div>
					{#if ghStatus.connected}
						<button
							class="text-xs px-3 py-1.5 rounded border border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/30 text-red-700 dark:text-red-400 disabled:opacity-50"
							disabled={ghDisconnecting}
							onclick={handleDisconnectGitHub}
						>
							{ghDisconnecting ? 'Disconnecting...' : 'Disconnect'}
						</button>
					{:else}
						<a
							href="/auth/github/connect"
							class="inline-flex items-center text-xs px-3 py-1.5 rounded bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-200 font-medium"
						>
							Connect GitHub
						</a>
					{/if}
				</div>
			</div>
		</div>
	{/if}

	{#if feedback}
		<div
			class="mb-4 p-3 rounded-lg text-sm {feedback.ok
				? 'bg-green-50 text-green-800 dark:bg-green-900/30 dark:text-green-300'
				: 'bg-red-50 text-red-800 dark:bg-red-900/30 dark:text-red-300'}"
		>
			{feedback.message}
			<button
				class="ml-2 underline text-xs"
				onclick={() => (feedback = null)}>dismiss</button
			>
		</div>
	{/if}

	{#if kbStore.loading}
		<div class="text-center py-12 text-gray-500">Loading...</div>
	{:else if kbStore.kbs.length === 0}
		<div class="text-center py-12 text-gray-500">
			<p>No knowledge bases registered.</p>
			<p class="text-sm mt-2">Add a KB or configure one in config.yaml.</p>
		</div>
	{:else}
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
			<table class="w-full text-sm">
				<thead class="bg-gray-50 dark:bg-gray-700">
					<tr>
						<th class="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300"
							>Name</th
						>
						<th class="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300"
							>Type</th
						>
						<th class="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300"
							>Source</th
						>
						<th
							class="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300"
							>Entries</th
						>
						<th class="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300"
							>Last Indexed</th
						>
						<th class="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300"
							>Actions</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-100 dark:divide-gray-700">
					{#each kbStore.kbs as kb}
						<tr class="hover:bg-gray-50 dark:hover:bg-gray-750">
							<td class="px-4 py-3">
								<div class="font-medium text-gray-900 dark:text-gray-100">
									{kb.name}
								</div>
								{#if kb.description}
									<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
										{kb.description}
									</div>
								{/if}
							</td>
							<td class="px-4 py-3 text-gray-600 dark:text-gray-400">{kb.type}</td>
							<td class="px-4 py-3">
								<span
									class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
									{kb.source === 'config'
										? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300'
										: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'}"
								>
									{kb.source}
								</span>
							</td>
							<td class="px-4 py-3 text-right text-gray-600 dark:text-gray-400"
								>{kb.entries}</td
							>
							<td class="px-4 py-3 text-gray-600 dark:text-gray-400 text-xs">
								{kb.last_indexed
									? new Date(kb.last_indexed).toLocaleString()
									: 'never'}
							</td>
							<td class="px-4 py-3 text-right">
								<div class="flex items-center justify-end gap-2">
									<a
										href="/settings/kbs/{encodeURIComponent(kb.name)}"
										class="text-xs px-2 py-1 rounded border border-blue-300 dark:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 text-blue-700 dark:text-blue-400"
									>
										Manage
									</a>
									<button
										class="text-xs px-2 py-1 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
										disabled={healthLoading === kb.name}
										onclick={() => handleHealth(kb.name)}
									>
										{healthLoading === kb.name ? '...' : 'Health'}
									</button>
									<button
										class="text-xs px-2 py-1 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
										disabled={reindexing === kb.name}
										onclick={() => handleReindex(kb.name)}
									>
										{reindexing === kb.name ? 'Reindexing...' : 'Reindex'}
									</button>
									{#if kb.source !== 'config'}
										<button
											class="text-xs px-2 py-1 rounded border border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/30 text-red-700 dark:text-red-400"
											onclick={() => (confirmDelete = kb.name)}
										>
											Remove
										</button>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}

	{#if healthResult}
		<div class="mt-4 p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
			<div class="flex items-center justify-between mb-2">
				<h3 class="font-medium text-gray-900 dark:text-gray-100">
					Health: {healthResult.name}
				</h3>
				<button
					class="text-xs text-gray-500 underline"
					onclick={() => (healthResult = null)}>close</button
				>
			</div>
			<div class="grid grid-cols-2 gap-3 text-sm">
				<div>
					Status:
					<span class={healthResult.healthy ? 'text-green-600' : 'text-red-600'}>
						{healthResult.healthy ? 'Healthy' : 'Unhealthy'}
					</span>
				</div>
				<div>Path exists: {healthResult.path_exists ? 'Yes' : 'No'}</div>
				<div>Files on disk: {healthResult.file_count}</div>
				<div>Indexed entries: {healthResult.entry_count}</div>
				<div>Last indexed: {healthResult.last_indexed || 'never'}</div>
				<div>Source: {healthResult.source}</div>
			</div>
		</div>
	{/if}

	<!-- Ephemeral KBs (admin only) -->
	{#if isAdmin && ephemeralKBs.length > 0}
		<div class="mt-6">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
				Ephemeral Knowledge Bases
			</h2>
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
				<table class="w-full text-sm">
					<thead class="bg-gray-50 dark:bg-gray-700">
						<tr>
							<th class="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300"
								>Name</th
							>
							<th class="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300"
								>TTL</th
							>
							<th class="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300"
								>Status</th
							>
							<th
								class="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-300"
								>Actions</th
							>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-100 dark:divide-gray-700">
						{#each ephemeralKBs as ekb}
							<tr class="hover:bg-gray-50 dark:hover:bg-gray-750">
								<td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100"
									>{ekb.name}</td
								>
								<td class="px-4 py-3 text-gray-600 dark:text-gray-400">
									{ekb.ttl ? `${Math.round(ekb.ttl / 60)}m` : 'N/A'}
								</td>
								<td class="px-4 py-3">
									<span
										class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
										{ekb.expired
											? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
											: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'}"
									>
										{ekb.expired ? 'Expired' : 'Active'}
									</span>
								</td>
								<td class="px-4 py-3 text-right">
									<button
										class="text-xs px-2 py-1 rounded border border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/30 text-red-700 dark:text-red-400 disabled:opacity-50"
										disabled={expiring === ekb.name}
										onclick={() => handleForceExpire(ekb.name)}
									>
										{expiring === ekb.name ? 'Expiring...' : 'Force Expire'}
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>

<!-- Add KB Dialog -->
{#if showAddDialog}
	<div
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
		role="dialog"
		aria-modal="true"
	>
		<div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
				Add Knowledge Base
			</h2>

			{#if addError}
				<div class="mb-3 p-2 rounded bg-red-50 dark:bg-red-900/30 text-red-800 dark:text-red-300 text-sm">
					{addError}
				</div>
			{/if}

			<div class="space-y-4">
				<div>
					<label
						for="kb-name"
						class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>Name</label
					>
					<input
						id="kb-name"
						type="text"
						bind:value={addName}
						placeholder="my-kb"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
					/>
				</div>
				<div>
					<label
						for="kb-path"
						class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>Path</label
					>
					<input
						id="kb-path"
						type="text"
						bind:value={addPath}
						placeholder="/path/to/kb"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
					/>
				</div>
				<div>
					<label
						for="kb-type"
						class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>Type</label
					>
					<select
						id="kb-type"
						bind:value={addType}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
					>
						<option value="generic">generic</option>
						<option value="research">research</option>
						<option value="events">events</option>
						<option value="zettelkasten">zettelkasten</option>
						<option value="software-kb">software-kb</option>
						<option value="encyclopedia">encyclopedia</option>
					</select>
				</div>
				<div>
					<label
						for="kb-desc"
						class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>Description</label
					>
					<input
						id="kb-desc"
						type="text"
						bind:value={addDescription}
						placeholder="Optional description"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
					/>
				</div>
			</div>

			<div class="flex justify-end gap-3 mt-6">
				<button
					class="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
					onclick={() => (showAddDialog = false)}
				>
					Cancel
				</button>
				<button
					class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
					disabled={adding || !addName.trim() || !addPath.trim()}
					onclick={handleAdd}
				>
					{adding ? 'Adding...' : 'Add KB'}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Delete Confirmation Dialog -->
{#if confirmDelete}
	<div
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
		role="dialog"
		aria-modal="true"
	>
		<div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Remove KB</h2>
			<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
				Remove <strong>{confirmDelete}</strong> from the registry? Files will not be deleted.
			</p>

			{#if deleteError}
				<div class="mb-3 p-2 rounded bg-red-50 dark:bg-red-900/30 text-red-800 dark:text-red-300 text-sm">
					{deleteError}
				</div>
			{/if}

			<div class="flex justify-end gap-3">
				<button
					class="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
					onclick={() => {
						confirmDelete = null;
						deleteError = null;
					}}
				>
					Cancel
				</button>
				<button
					class="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
					disabled={deleting}
					onclick={() => confirmDelete && handleDelete(confirmDelete)}
				>
					{deleting ? 'Removing...' : 'Remove'}
				</button>
			</div>
		</div>
	</div>
{/if}
