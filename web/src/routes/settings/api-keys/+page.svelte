<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import { api, ApiError } from '$lib/api/client';
	import { onMount } from 'svelte';

	type ApiKeyEntry = { provider: string; model: string; created_at: string };

	let keys = $state<ApiKeyEntry[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Form state
	let formProvider = $state('anthropic');
	let formApiKey = $state('');
	let formModel = $state('');
	let saving = $state(false);
	let saveResult = $state<{ ok: boolean; message: string } | null>(null);

	// Delete state
	let confirmDelete = $state<string | null>(null);
	let deleting = $state(false);

	const providerLabels: Record<string, string> = {
		anthropic: 'Anthropic',
		openai: 'OpenAI',
		gemini: 'Google Gemini',
		openrouter: 'OpenRouter',
		ollama: 'Ollama'
	};

	const modelPlaceholders: Record<string, string> = {
		anthropic: 'claude-sonnet-4-20250514',
		openai: 'gpt-4o',
		gemini: 'gemini-2.0-flash',
		openrouter: 'anthropic/claude-sonnet-4',
		ollama: 'llama3.2'
	};

	async function loadKeys() {
		loading = true;
		error = null;
		try {
			const result = await api.listUserApiKeys();
			keys = result.keys;
		} catch (e) {
			error = e instanceof ApiError ? e.detail : 'Failed to load API keys';
		} finally {
			loading = false;
		}
	}

	async function handleSave() {
		if (!formApiKey.trim()) return;
		saving = true;
		saveResult = null;
		try {
			await api.storeUserApiKey(formProvider, formApiKey, formModel);
			saveResult = { ok: true, message: `Key saved for ${providerLabels[formProvider] || formProvider}` };
			formApiKey = '';
			formModel = '';
			await loadKeys();
		} catch (e) {
			saveResult = {
				ok: false,
				message: e instanceof ApiError ? e.detail : 'Failed to save key'
			};
		} finally {
			saving = false;
		}
	}

	async function handleDelete(provider: string) {
		deleting = true;
		try {
			await api.deleteUserApiKey(provider);
			confirmDelete = null;
			await loadKeys();
		} catch (e) {
			error = e instanceof ApiError ? e.detail : 'Failed to delete key';
		} finally {
			deleting = false;
		}
	}

	async function testConnection() {
		saveResult = null;
		try {
			const result = await api.testAIConnection();
			saveResult = { ok: result.ok, message: result.message };
		} catch (e) {
			saveResult = {
				ok: false,
				message: e instanceof ApiError ? e.detail : 'Connection test failed'
			};
		}
	}

	onMount(() => {
		loadKeys();
	});
</script>

<svelte:head><title>My API Keys — Pyrite</title></svelte:head>

<Topbar title="My API Keys" />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mx-auto max-w-2xl space-y-8">
		<div>
			<h1 class="page-title mb-2 text-2xl font-bold">My API Keys</h1>
			<p class="text-sm text-zinc-500 dark:text-zinc-400">
				Bring your own LLM API key for AI features. Your key is encrypted and used only for
				your requests.
			</p>
		</div>

		{#if loading}
			<div class="flex items-center gap-2 text-sm text-zinc-500">
				<svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
					<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
					<path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
				</svg>
				Loading...
			</div>
		{:else}
			<!-- Configured Keys -->
			{#if keys.length > 0}
				<section>
					<h2 class="mb-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
						Configured Providers
					</h2>
					<div class="space-y-2">
						{#each keys as key}
							<div
								class="flex items-center justify-between rounded-md border border-zinc-200 px-4 py-3 dark:border-zinc-700"
							>
								<div>
									<span class="text-sm font-medium text-zinc-900 dark:text-zinc-100">
										{providerLabels[key.provider] || key.provider}
									</span>
									{#if key.model}
										<span class="ml-2 text-xs text-zinc-500">({key.model})</span>
									{/if}
									<p class="text-xs text-zinc-400">
										Added {new Date(key.created_at).toLocaleDateString()}
									</p>
								</div>
								<div class="flex items-center gap-2">
									{#if confirmDelete === key.provider}
										<button
											onclick={() => handleDelete(key.provider)}
											disabled={deleting}
											class="rounded-md bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
										>
											{deleting ? 'Deleting...' : 'Confirm'}
										</button>
										<button
											onclick={() => (confirmDelete = null)}
											class="rounded-md border border-zinc-300 px-3 py-1 text-xs font-medium hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
										>
											Cancel
										</button>
									{:else}
										<button
											onclick={() => (confirmDelete = key.provider)}
											class="rounded-md border border-zinc-300 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50 dark:border-zinc-600 dark:text-red-400 dark:hover:bg-zinc-700"
										>
											Remove
										</button>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</section>
			{/if}

			<!-- Add / Update Key -->
			<section>
				<h2 class="mb-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
					{keys.length > 0 ? 'Add or Update Key' : 'Add Your First Key'}
				</h2>
				<div class="space-y-4 rounded-lg border border-zinc-200 p-4 dark:border-zinc-700">
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300"
								>Provider</label
							>
							<p class="text-xs text-zinc-500">LLM service to configure</p>
						</div>
						<select
							bind:value={formProvider}
							class="w-48 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						>
							<option value="anthropic">Anthropic</option>
							<option value="openai">OpenAI</option>
							<option value="gemini">Google Gemini</option>
							<option value="openrouter">OpenRouter</option>
							<option value="ollama">Ollama</option>
						</select>
					</div>
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300"
								>API Key</label
							>
							<p class="text-xs text-zinc-500">
								{formProvider === 'ollama'
									? 'Not required for local Ollama'
									: 'Your personal API key for this provider'}
							</p>
						</div>
						<input
							type="password"
							bind:value={formApiKey}
							placeholder={formProvider === 'ollama' ? 'Not required' : 'sk-...'}
							class="w-48 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						/>
					</div>
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300">Model</label
							>
							<p class="text-xs text-zinc-500">Optional model override</p>
						</div>
						<input
							type="text"
							bind:value={formModel}
							placeholder={modelPlaceholders[formProvider] ?? ''}
							class="w-48 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						/>
					</div>
					<div class="flex items-center justify-between">
						<div>
							{#if saveResult}
								<span
									class="text-sm {saveResult.ok
										? 'text-green-600 dark:text-green-400'
										: 'text-red-500'}"
								>
									{saveResult.message}
								</span>
							{/if}
						</div>
						<div class="flex gap-2">
							<button
								onclick={testConnection}
								class="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
							>
								Test
							</button>
							<button
								onclick={handleSave}
								disabled={saving || !formApiKey.trim()}
								class="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
							>
								{saving ? 'Saving...' : 'Save Key'}
							</button>
						</div>
					</div>
				</div>
			</section>

			<!-- Info -->
			<section class="rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800/50 dark:text-zinc-400">
				<h3 class="mb-2 font-semibold text-zinc-800 dark:text-zinc-200">How it works</h3>
				<ul class="list-inside list-disc space-y-1">
					<li>Your key is encrypted at rest and never shared with other users.</li>
					<li>When you use AI features (summarize, auto-tag, chat), your key is used instead of the server default.</li>
					<li>If you remove your key, AI features fall back to the server-configured provider.</li>
					<li>You can configure keys for multiple providers; the most recently updated one is used.</li>
				</ul>
			</section>

			{#if error}
				<p class="text-sm text-red-500">{error}</p>
			{/if}
		{/if}

		<div class="pt-2">
			<a
				href="/settings"
				class="text-sm text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
			>
				&larr; Back to Settings
			</a>
		</div>
	</div>
</div>
