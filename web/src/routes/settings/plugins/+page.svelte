<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import { api } from '$lib/api/client';
	import { onMount } from 'svelte';
	import type { PluginInfo, PluginDetail } from '$lib/api/types';

	let plugins = $state<PluginInfo[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let selectedPlugin = $state<PluginDetail | null>(null);
	let loadingDetail = $state(false);

	onMount(async () => {
		try {
			const res = await api.getPlugins();
			plugins = res.plugins;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load plugins';
		} finally {
			loading = false;
		}
	});

	async function selectPlugin(name: string) {
		loadingDetail = true;
		try {
			selectedPlugin = await api.getPlugin(name);
		} catch {
			// ignore
		} finally {
			loadingDetail = false;
		}
	}
</script>

<Topbar title="Plugins" />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mx-auto max-w-3xl">
		<div class="mb-6">
			<h2 class="text-lg font-semibold text-zinc-900 dark:text-zinc-100">Installed Plugins</h2>
			<p class="text-sm text-zinc-500">
				Extensions that add entry types, tools, and hooks to Pyrite.
			</p>
		</div>

		{#if loading}
			<p class="text-zinc-400">Loading plugins...</p>
		{:else if error}
			<p class="text-red-500">{error}</p>
		{:else if plugins.length === 0}
			<div class="rounded-lg border border-zinc-200 p-8 text-center dark:border-zinc-700">
				<p class="text-zinc-500">No plugins installed.</p>
				<p class="mt-2 text-sm text-zinc-400">
					Install plugins via pip and they'll appear here automatically.
				</p>
			</div>
		{:else}
			<div class="space-y-3">
				{#each plugins as plugin}
					<button
						class="w-full rounded-lg border border-zinc-200 p-4 text-left transition hover:border-blue-300 hover:shadow-sm dark:border-zinc-700 dark:hover:border-blue-600
						{selectedPlugin?.name === plugin.name
							? 'border-blue-400 bg-blue-50/50 dark:border-blue-500 dark:bg-blue-950/20'
							: ''}"
						onclick={() => selectPlugin(plugin.name)}
					>
						<div class="flex items-center justify-between">
							<div>
								<h3 class="font-medium text-zinc-900 dark:text-zinc-100">
									{plugin.name}
								</h3>
								<div class="mt-1 flex flex-wrap gap-1.5">
									{#if plugin.entry_types.length > 0}
										<span
											class="inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
										>
											{plugin.entry_types.length} type{plugin.entry_types.length > 1
												? 's'
												: ''}
										</span>
									{/if}
									{#if plugin.tools.length > 0}
										<span
											class="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
										>
											{plugin.tools.length} tool{plugin.tools.length > 1 ? 's' : ''}
										</span>
									{/if}
									{#if plugin.hooks.length > 0}
										<span
											class="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
										>
											{plugin.hooks.length} hook{plugin.hooks.length > 1 ? 's' : ''}
										</span>
									{/if}
									{#if plugin.has_cli}
										<span
											class="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-300"
										>
											CLI
										</span>
									{/if}
								</div>
							</div>
							<span
								class="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300"
							>
								Active
							</span>
						</div>
					</button>
				{/each}
			</div>

			{#if selectedPlugin}
				<div class="mt-6 rounded-lg border border-zinc-200 p-5 dark:border-zinc-700">
					{#if loadingDetail}
						<p class="text-zinc-400">Loading...</p>
					{:else}
						<h3 class="mb-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
							{selectedPlugin.name}
						</h3>

						{#if Object.keys(selectedPlugin.entry_types).length > 0}
							<div class="mb-4">
								<h4 class="mb-1 text-sm font-medium text-zinc-700 dark:text-zinc-300">
									Entry Types
								</h4>
								<div class="flex flex-wrap gap-2">
									{#each Object.keys(selectedPlugin.entry_types) as typeName}
										<span
											class="rounded bg-purple-100 px-2 py-0.5 text-sm text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
										>
											{typeName}
										</span>
									{/each}
								</div>
							</div>
						{/if}

						{#if selectedPlugin.kb_types.length > 0}
							<div class="mb-4">
								<h4 class="mb-1 text-sm font-medium text-zinc-700 dark:text-zinc-300">
									KB Types
								</h4>
								<div class="flex flex-wrap gap-2">
									{#each selectedPlugin.kb_types as kbType}
										<span
											class="rounded bg-blue-100 px-2 py-0.5 text-sm text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
										>
											{kbType}
										</span>
									{/each}
								</div>
							</div>
						{/if}

						{#if Object.keys(selectedPlugin.tools).length > 0}
							<div class="mb-4">
								<h4 class="mb-1 text-sm font-medium text-zinc-700 dark:text-zinc-300">
									MCP Tools
								</h4>
								<div class="space-y-1">
									{#each Object.entries(selectedPlugin.tools) as [toolName, toolInfo]}
										<div class="flex items-center gap-2 text-sm">
											<span class="font-mono text-zinc-600 dark:text-zinc-400"
												>{toolName}</span
											>
											<span
												class="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-500 dark:bg-zinc-800"
											>
												{toolInfo.tier}
											</span>
											{#if toolInfo.description}
												<span class="text-zinc-400"
													>&mdash; {toolInfo.description}</span
												>
											{/if}
										</div>
									{/each}
								</div>
							</div>
						{/if}

						{#if Object.keys(selectedPlugin.hooks).length > 0}
							<div class="mb-4">
								<h4 class="mb-1 text-sm font-medium text-zinc-700 dark:text-zinc-300">
									Hooks
								</h4>
								<div class="flex flex-wrap gap-2">
									{#each Object.entries(selectedPlugin.hooks) as [hookName, count]}
										<span
											class="rounded bg-amber-100 px-2 py-0.5 text-sm text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
										>
											{hookName} ({count})
										</span>
									{/each}
								</div>
							</div>
						{/if}
					{/if}
				</div>
			{/if}
		{/if}
	</div>
</div>
