<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import ErrorState from '$lib/components/common/ErrorState.svelte';
	import { api } from '$lib/api/client';
	import { kbStore } from '$lib/stores/kbs.svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import type { UserInfo } from '$lib/api/types';
	import { onMount } from 'svelte';

	let users = $state<UserInfo[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchFilter = $state('');

	// Role editing
	let editingRole = $state<number | null>(null);
	let pendingRole = $state('');
	let roleUpdating = $state(false);

	// KB permission editing
	let expandedUser = $state<number | null>(null);
	let userPerms = $state<Record<string, string>>({});
	let permsLoading = $state(false);
	let grantKb = $state('');
	let grantRole = $state('read');
	let granting = $state(false);

	let feedback = $state<{ ok: boolean; message: string } | null>(null);

	async function loadUsers() {
		loading = true;
		error = null;
		try {
			const res = await api.listUsers();
			users = res.users;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load users';
		} finally {
			loading = false;
		}
	}

	async function handleSetRole(userId: number) {
		roleUpdating = true;
		try {
			await api.setUserRole(userId, pendingRole);
			users = users.map((u) => (u.id === userId ? { ...u, role: pendingRole } : u));
			editingRole = null;
			feedback = { ok: true, message: `Role updated to ${pendingRole}` };
		} catch (err) {
			feedback = { ok: false, message: err instanceof Error ? err.message : 'Failed to update role' };
		} finally {
			roleUpdating = false;
		}
	}

	async function loadUserPerms(userId: number) {
		if (expandedUser === userId) {
			expandedUser = null;
			return;
		}
		expandedUser = userId;
		permsLoading = true;
		try {
			const res = await api.getUserPermissions(userId);
			userPerms = res.permissions;
		} catch {
			userPerms = {};
		} finally {
			permsLoading = false;
		}
	}

	async function handleGrantPermission(userId: number) {
		if (!grantKb) return;
		granting = true;
		try {
			await api.grantKBPermission(grantKb, userId, grantRole);
			userPerms = { ...userPerms, [grantKb]: grantRole };
			grantKb = '';
			grantRole = 'read';
			feedback = { ok: true, message: 'Permission granted' };
		} catch (err) {
			feedback = { ok: false, message: err instanceof Error ? err.message : 'Grant failed' };
		} finally {
			granting = false;
		}
	}

	async function handleRevokePermission(userId: number, kbName: string) {
		try {
			await api.revokeKBPermission(kbName, userId);
			const { [kbName]: _, ...rest } = userPerms;
			userPerms = rest;
			feedback = { ok: true, message: `Revoked ${kbName} access` };
		} catch (err) {
			feedback = { ok: false, message: err instanceof Error ? err.message : 'Revoke failed' };
		}
	}

	onMount(() => {
		loadUsers();
		kbStore.load();
	});

	const filteredUsers = $derived(
		searchFilter.trim()
			? users.filter(
					(u) =>
						u.username.toLowerCase().includes(searchFilter.toLowerCase()) ||
						(u.display_name ?? '').toLowerCase().includes(searchFilter.toLowerCase())
				)
			: users
	);

	const isAdmin = $derived(authStore.isAdmin);

	const roleColors: Record<string, string> = {
		admin: 'bg-red-500/20 text-red-400',
		write: 'bg-blue-500/20 text-blue-400',
		read: 'bg-zinc-500/20 text-zinc-400',
	};
</script>

<svelte:head><title>Users — Pyrite</title></svelte:head>

<Topbar breadcrumbs={[{ label: 'Settings', href: '/settings' }, { label: 'Users' }]} />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mx-auto max-w-3xl">
		<div class="mb-6 flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Users</h1>
				<p class="mt-1 text-sm text-zinc-500">{users.length} registered user{users.length === 1 ? '' : 's'}</p>
			</div>
		</div>

		<!-- Feedback -->
		{#if feedback}
			<div class="mb-4 rounded-lg px-4 py-3 text-sm {feedback.ok ? 'border border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border border-red-500/30 bg-red-500/10 text-red-400'}">
				{feedback.message}
			</div>
		{/if}

		{#if error}
			<ErrorState message={error} onretry={loadUsers} />
		{:else if loading}
			<div class="flex items-center justify-center py-16 text-zinc-400">
				<svg class="mr-3 h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				Loading users...
			</div>
		{:else}
			<!-- Search filter -->
			{#if users.length > 5}
				<div class="mb-4">
					<input
						type="text"
						bind:value={searchFilter}
						placeholder="Filter users..."
						class="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-gold-400 dark:border-zinc-700 dark:bg-zinc-800"
					/>
				</div>
			{/if}

			<!-- User list -->
			<div class="space-y-2">
				{#each filteredUsers as user (user.id)}
					<div class="rounded-lg border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-800">
						<div class="flex items-center justify-between px-4 py-3">
							<div class="flex items-center gap-3">
								<!-- Avatar -->
								{#if user.avatar_url}
									<img src={user.avatar_url} alt="" class="h-8 w-8 rounded-full" />
								{:else}
									<div class="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-200 text-xs font-medium text-zinc-600 dark:bg-zinc-700 dark:text-zinc-400">
										{user.username.charAt(0).toUpperCase()}
									</div>
								{/if}

								<div>
									<div class="flex items-center gap-2">
										<span class="font-medium text-zinc-900 dark:text-zinc-100">{user.username}</span>
										{#if user.display_name}
											<span class="text-sm text-zinc-500">({user.display_name})</span>
										{/if}
									</div>
									<div class="flex items-center gap-2 text-xs text-zinc-500">
										<span>{user.auth_provider}</span>
									</div>
								</div>
							</div>

							<div class="flex items-center gap-2">
								<!-- Role badge -->
								{#if editingRole === user.id}
									<select
										bind:value={pendingRole}
										class="rounded border border-zinc-300 bg-white px-2 py-1 text-xs dark:border-zinc-700 dark:bg-zinc-800"
									>
										<option value="read">read</option>
										<option value="write">write</option>
										<option value="admin">admin</option>
									</select>
									<button
										onclick={() => handleSetRole(user.id)}
										disabled={roleUpdating}
										class="rounded bg-gold-500 px-2 py-1 text-xs font-medium text-zinc-900 hover:bg-gold-400 disabled:opacity-50"
									>
										{roleUpdating ? '...' : 'Save'}
									</button>
									<button
										onclick={() => (editingRole = null)}
										class="text-xs text-zinc-500 hover:text-zinc-300"
									>
										Cancel
									</button>
								{:else}
									<span class="rounded-full px-2 py-0.5 text-xs font-medium {roleColors[user.role] ?? roleColors.read}">
										{user.role}
									</span>
									{#if isAdmin}
										<button
											onclick={() => { editingRole = user.id; pendingRole = user.role; }}
											class="text-xs text-zinc-500 hover:text-zinc-300"
											title="Change role"
										>
											Edit
										</button>
									{/if}
								{/if}

								<!-- Expand KB permissions -->
								{#if isAdmin}
									<button
										onclick={() => loadUserPerms(user.id)}
										class="text-xs text-zinc-500 hover:text-zinc-300"
										title="KB permissions"
									>
										{expandedUser === user.id ? 'Hide' : 'KBs'}
									</button>
								{/if}
							</div>
						</div>

						<!-- KB permissions panel -->
						{#if expandedUser === user.id}
							<div class="border-t border-zinc-100 px-4 py-3 dark:border-zinc-700">
								{#if permsLoading}
									<p class="text-xs text-zinc-500">Loading permissions...</p>
								{:else}
									<p class="mb-2 text-xs font-medium text-zinc-500">KB Permissions</p>
									{#if Object.keys(userPerms).length > 0}
										<div class="mb-2 space-y-1">
											{#each Object.entries(userPerms) as [kb, role]}
												<div class="flex items-center justify-between rounded bg-zinc-50 px-2 py-1 text-xs dark:bg-zinc-800/50">
													<span class="text-zinc-700 dark:text-zinc-300">{kb}</span>
													<div class="flex items-center gap-2">
														<span class="rounded-full px-1.5 py-0.5 {roleColors[role] ?? roleColors.read}">{role}</span>
														<button
															onclick={() => handleRevokePermission(user.id, kb)}
															class="text-zinc-400 hover:text-red-400"
															title="Revoke"
														>&times;</button>
													</div>
												</div>
											{/each}
										</div>
									{:else}
										<p class="mb-2 text-xs text-zinc-500">No explicit KB grants. Uses global role.</p>
									{/if}

									<!-- Grant new permission -->
									<div class="flex items-center gap-2">
										<select
											bind:value={grantKb}
											class="flex-1 rounded border border-zinc-300 bg-white px-2 py-1 text-xs dark:border-zinc-700 dark:bg-zinc-800"
										>
											<option value="">Select KB...</option>
											{#each kbStore.kbs as kb}
												{#if !userPerms[kb.name]}
													<option value={kb.name}>{kb.name}</option>
												{/if}
											{/each}
										</select>
										<select
											bind:value={grantRole}
											class="rounded border border-zinc-300 bg-white px-2 py-1 text-xs dark:border-zinc-700 dark:bg-zinc-800"
										>
											<option value="read">read</option>
											<option value="write">write</option>
											<option value="admin">admin</option>
										</select>
										<button
											onclick={() => handleGrantPermission(user.id)}
											disabled={!grantKb || granting}
											class="rounded bg-gold-500 px-2 py-1 text-xs font-medium text-zinc-900 hover:bg-gold-400 disabled:opacity-50"
										>
											Grant
										</button>
									</div>
								{/if}
							</div>
						{/if}
					</div>
				{/each}
			</div>

			{#if filteredUsers.length === 0 && searchFilter.trim()}
				<p class="py-8 text-center text-sm text-zinc-500">No users matching "{searchFilter}"</p>
			{/if}
		{/if}
	</div>
</div>
