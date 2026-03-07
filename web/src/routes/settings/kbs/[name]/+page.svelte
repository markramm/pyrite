<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import { api, ApiError } from '$lib/api/client';
	import { authStore } from '$lib/stores/auth.svelte';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import type {
		KBInfo,
		KBPermissionGrant,
		KBHealthResponse,
		UserInfo
	} from '$lib/api/types';

	const kbName = $derived($page.params.name);
	let kb = $state<KBInfo | null>(null);
	let permissions = $state<KBPermissionGrant[]>([]);
	let users = $state<UserInfo[]>([]);
	let health = $state<KBHealthResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Default role editing
	let savingRole = $state(false);
	let roleMessage = $state<string | null>(null);

	// Description editing
	let editingDescription = $state(false);
	let descriptionDraft = $state('');
	let savingDescription = $state(false);

	// Grant form
	let grantUserId = $state<number | null>(null);
	let grantRole = $state('read');
	let granting = $state(false);
	let grantError = $state<string | null>(null);

	// Reindex
	let reindexing = $state(false);

	// Health
	let healthLoading = $state(false);

	let feedback = $state<{ ok: boolean; message: string } | null>(null);

	const breadcrumbs = $derived([
		{ label: 'Knowledge Bases', href: '/settings/kbs' },
		{ label: kbName }
	]);

	const isAdmin = $derived(authStore.isAdmin);

	onMount(async () => {
		try {
			const [kbData, permData] = await Promise.all([
				api.getKB(kbName),
				isAdmin ? api.getKBPermissions(kbName).catch(() => ({ permissions: [] })) : Promise.resolve({ permissions: [] as KBPermissionGrant[] })
			]);
			kb = kbData;
			permissions = permData.permissions;

			if (isAdmin) {
				const userData = await api.listUsers().catch(() => ({ users: [] }));
				users = userData.users;
			}
		} catch (e) {
			error = e instanceof ApiError ? e.detail : 'Failed to load KB';
		} finally {
			loading = false;
		}
	});

	async function handleDefaultRoleChange(newRole: string) {
		if (!kb) return;
		savingRole = true;
		roleMessage = null;
		try {
			const roleValue = newRole === '' ? null : newRole;
			await api.updateKBDefaultRole(kbName, roleValue);
			kb = { ...kb, default_role: roleValue };
			roleMessage = 'Default role updated';
			setTimeout(() => (roleMessage = null), 3000);
		} catch (e) {
			roleMessage = e instanceof ApiError ? e.detail : 'Failed to update';
		} finally {
			savingRole = false;
		}
	}

	async function handleSaveDescription() {
		if (!kb) return;
		savingDescription = true;
		try {
			await api.updateKB(kbName, { description: descriptionDraft });
			kb = { ...kb, description: descriptionDraft };
			editingDescription = false;
			feedback = { ok: true, message: 'Description updated' };
		} catch (e) {
			feedback = { ok: false, message: e instanceof ApiError ? e.detail : 'Failed to update' };
		} finally {
			savingDescription = false;
		}
	}

	async function handleGrant() {
		if (grantUserId === null) return;
		granting = true;
		grantError = null;
		try {
			await api.grantKBPermission(kbName, grantUserId, grantRole);
			// Refresh permissions
			const permData = await api.getKBPermissions(kbName);
			permissions = permData.permissions;
			grantUserId = null;
			grantRole = 'read';
			feedback = { ok: true, message: 'Permission granted' };
		} catch (e) {
			grantError = e instanceof ApiError ? e.detail : 'Failed to grant permission';
		} finally {
			granting = false;
		}
	}

	async function handleRevoke(userId: number, username: string) {
		try {
			await api.revokeKBPermission(kbName, userId);
			permissions = permissions.filter((p) => p.user_id !== userId);
			feedback = { ok: true, message: `Revoked access for ${username}` };
		} catch (e) {
			feedback = {
				ok: false,
				message: e instanceof ApiError ? e.detail : 'Failed to revoke'
			};
		}
	}

	async function handleReindex() {
		reindexing = true;
		try {
			const result = await api.reindexKB(kbName);
			feedback = {
				ok: true,
				message: `Reindexed: +${result.added} added, ~${result.updated} updated, -${result.removed} removed`
			};
			// Refresh KB data
			kb = await api.getKB(kbName);
		} catch (e) {
			feedback = { ok: false, message: e instanceof ApiError ? e.detail : 'Reindex failed' };
		} finally {
			reindexing = false;
		}
	}

	async function handleHealthCheck() {
		healthLoading = true;
		health = null;
		try {
			health = await api.getKBHealth(kbName);
		} catch (e) {
			feedback = {
				ok: false,
				message: e instanceof ApiError ? e.detail : 'Health check failed'
			};
		} finally {
			healthLoading = false;
		}
	}

	// Filter users for grant dropdown — exclude those who already have a grant
	const availableUsers = $derived(
		users.filter((u) => !permissions.some((p) => p.user_id === u.id))
	);
</script>

<Topbar {breadcrumbs} />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mx-auto max-w-2xl space-y-6">
		{#if loading}
			<div class="text-center py-12 text-gray-500">Loading...</div>
		{:else if error}
			<div class="p-4 bg-red-50 dark:bg-red-900/30 text-red-800 dark:text-red-300 rounded-lg">
				{error}
			</div>
		{:else if kb}
			{#if feedback}
				<div
					class="p-3 rounded-lg text-sm {feedback.ok
						? 'bg-green-50 text-green-800 dark:bg-green-900/30 dark:text-green-300'
						: 'bg-red-50 text-red-800 dark:bg-red-900/30 dark:text-red-300'}"
				>
					{feedback.message}
					<button class="ml-2 underline text-xs" onclick={() => (feedback = null)}
						>dismiss</button
					>
				</div>
			{/if}

			<!-- KB Info Section -->
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-5">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
					KB Information
				</h2>
				<div class="grid grid-cols-2 gap-4 text-sm">
					<div>
						<span class="text-gray-500 dark:text-gray-400">Name</span>
						<div class="font-medium text-gray-900 dark:text-gray-100">{kb.name}</div>
					</div>
					<div>
						<span class="text-gray-500 dark:text-gray-400">Type</span>
						<div class="text-gray-900 dark:text-gray-100">{kb.type}</div>
					</div>
					<div>
						<span class="text-gray-500 dark:text-gray-400">Source</span>
						<div>
							<span
								class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
								{kb.source === 'config'
									? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300'
									: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'}"
							>
								{kb.source}
							</span>
						</div>
					</div>
					<div>
						<span class="text-gray-500 dark:text-gray-400">Entries</span>
						<div class="text-gray-900 dark:text-gray-100">{kb.entries}</div>
					</div>
					<div class="col-span-2">
						<span class="text-gray-500 dark:text-gray-400">Path</span>
						<div class="text-gray-900 dark:text-gray-100 font-mono text-xs">{kb.path}</div>
					</div>
					<div class="col-span-2">
						<span class="text-gray-500 dark:text-gray-400">Last Indexed</span>
						<div class="text-gray-900 dark:text-gray-100">
							{kb.last_indexed ? new Date(kb.last_indexed).toLocaleString() : 'Never'}
						</div>
					</div>
					<div class="col-span-2">
						<div class="flex items-center justify-between">
							<span class="text-gray-500 dark:text-gray-400">Description</span>
							{#if !editingDescription}
								<button
									class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
									onclick={() => {
										descriptionDraft = kb?.description || '';
										editingDescription = true;
									}}>Edit</button
								>
							{/if}
						</div>
						{#if editingDescription}
							<div class="mt-1 flex gap-2">
								<input
									type="text"
									bind:value={descriptionDraft}
									class="flex-1 px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
								/>
								<button
									class="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
									disabled={savingDescription}
									onclick={handleSaveDescription}
								>
									Save
								</button>
								<button
									class="px-3 py-1.5 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
									onclick={() => (editingDescription = false)}
								>
									Cancel
								</button>
							</div>
						{:else}
							<div class="text-gray-900 dark:text-gray-100">
								{kb.description || 'No description'}
							</div>
						{/if}
					</div>
				</div>

				<div class="flex gap-2 mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
					<button
						class="text-xs px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
						disabled={reindexing}
						onclick={handleReindex}
					>
						{reindexing ? 'Reindexing...' : 'Reindex'}
					</button>
					<button
						class="text-xs px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
						disabled={healthLoading}
						onclick={handleHealthCheck}
					>
						{healthLoading ? 'Checking...' : 'Health Check'}
					</button>
				</div>
			</div>

			<!-- Health Result -->
			{#if health}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-5">
					<div class="flex items-center justify-between mb-3">
						<h3 class="font-medium text-gray-900 dark:text-gray-100">Health Check</h3>
						<button
							class="text-xs text-gray-500 underline"
							onclick={() => (health = null)}>close</button
						>
					</div>
					<div class="grid grid-cols-2 gap-3 text-sm">
						<div>
							Status:
							<span class={health.healthy ? 'text-green-600' : 'text-red-600'}>
								{health.healthy ? 'Healthy' : 'Unhealthy'}
							</span>
						</div>
						<div>Path exists: {health.path_exists ? 'Yes' : 'No'}</div>
						<div>Files on disk: {health.file_count}</div>
						<div>Indexed entries: {health.entry_count}</div>
					</div>
				</div>
			{/if}

			<!-- Access Control Section (admin only) -->
			{#if isAdmin}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-5">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
						Access Control
					</h2>

					<!-- Default Role -->
					<div class="mb-6">
						<label
							for="default-role"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>
							Default Role
						</label>
						<p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
							Who can access this KB by default. "None" = private (explicit grants only).
						</p>
						<div class="flex items-center gap-3">
							<select
								id="default-role"
								value={kb.default_role || ''}
								class="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
								disabled={savingRole}
								onchange={(e) => handleDefaultRoleChange(e.currentTarget.value)}
							>
								<option value="">Use global role</option>
								<option value="read">Read (public)</option>
								<option value="write">Write</option>
								<option value="none">None (private)</option>
							</select>
							{#if roleMessage}
								<span class="text-xs text-green-600 dark:text-green-400"
									>{roleMessage}</span
								>
							{/if}
						</div>
					</div>

					<!-- Explicit Grants -->
					<div>
						<h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Explicit Grants
						</h3>

						{#if permissions.length === 0}
							<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
								No explicit permission grants.
							</p>
						{:else}
							<div
								class="mb-4 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
							>
								<table class="w-full text-sm">
									<thead class="bg-gray-50 dark:bg-gray-700">
										<tr>
											<th
												class="text-left px-3 py-2 font-medium text-gray-600 dark:text-gray-300"
												>User</th
											>
											<th
												class="text-left px-3 py-2 font-medium text-gray-600 dark:text-gray-300"
												>Role</th
											>
											<th
												class="text-left px-3 py-2 font-medium text-gray-600 dark:text-gray-300"
												>Granted</th
											>
											<th class="px-3 py-2"></th>
										</tr>
									</thead>
									<tbody class="divide-y divide-gray-100 dark:divide-gray-700">
										{#each permissions as perm}
											<tr>
												<td class="px-3 py-2 text-gray-900 dark:text-gray-100"
													>{perm.username}</td
												>
												<td class="px-3 py-2">
													<span
														class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
														{perm.role === 'admin'
															? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
															: perm.role === 'write'
																? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
																: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'}"
													>
														{perm.role}
													</span>
												</td>
												<td class="px-3 py-2 text-gray-500 text-xs">
													{new Date(perm.created_at).toLocaleDateString()}
												</td>
												<td class="px-3 py-2 text-right">
													<button
														class="text-xs text-red-600 dark:text-red-400 hover:underline"
														onclick={() =>
															handleRevoke(perm.user_id, perm.username)}
													>
														Revoke
													</button>
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						{/if}

						<!-- Add Grant Form -->
						{#if availableUsers.length > 0}
							<div class="flex items-end gap-2">
								<div class="flex-1">
									<label
										for="grant-user"
										class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
										>User</label
									>
									<select
										id="grant-user"
										bind:value={grantUserId}
										class="w-full px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
									>
										<option value={null}>Select user...</option>
										{#each availableUsers as user}
											<option value={user.id}>
												{user.username}
												{user.display_name ? `(${user.display_name})` : ''}
											</option>
										{/each}
									</select>
								</div>
								<div>
									<label
										for="grant-role"
										class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
										>Role</label
									>
									<select
										id="grant-role"
										bind:value={grantRole}
										class="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
									>
										<option value="read">Read</option>
										<option value="write">Write</option>
										<option value="admin">Admin</option>
									</select>
								</div>
								<button
									class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
									disabled={granting || grantUserId === null}
									onclick={handleGrant}
								>
									{granting ? '...' : 'Grant'}
								</button>
							</div>
							{#if grantError}
								<p class="mt-1 text-xs text-red-600 dark:text-red-400">
									{grantError}
								</p>
							{/if}
						{:else if users.length > 0}
							<p class="text-xs text-gray-500 dark:text-gray-400">
								All users already have explicit grants.
							</p>
						{/if}
					</div>
				</div>
			{/if}
		{/if}
	</div>
</div>
