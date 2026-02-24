<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { settingsStore } from '$lib/stores/settings.svelte';
	import { api } from '$lib/api/client';
	import { onMount } from 'svelte';

	let testingConnection = $state(false);
	let connectionResult = $state<{ ok: boolean; message: string } | null>(null);

	onMount(() => {
		settingsStore.load();
	});

	function setTheme(theme: string) {
		settingsStore.set('appearance.theme', theme);
		if (theme === 'dark' || theme === 'light') {
			uiStore.theme = theme;
			if (typeof window !== 'undefined') {
				localStorage.setItem('pyrite-theme', theme);
				document.documentElement.classList.toggle('dark', theme === 'dark');
			}
		}
	}

	function setSetting(key: string, value: string) {
		settingsStore.set(key, value);
	}

	async function testAIConnection() {
		testingConnection = true;
		connectionResult = null;
		try {
			const status = await api.getAIStatus();
			if (status.configured) {
				connectionResult = {
					ok: true,
					message: `Connected: ${status.provider} (${status.model ?? 'default model'})`
				};
			} else {
				connectionResult = {
					ok: false,
					message: 'Not configured — set a provider and API key'
				};
			}
		} catch (e) {
			connectionResult = {
				ok: false,
				message: e instanceof Error ? e.message : 'Connection failed'
			};
		} finally {
			testingConnection = false;
		}
	}

	const currentTheme = $derived(settingsStore.get('appearance.theme', uiStore.theme));
	const fontSize = $derived(settingsStore.get('appearance.fontSize', '14'));
	const defaultKb = $derived(settingsStore.get('general.defaultKb', ''));
	const itemsPerPage = $derived(settingsStore.get('general.itemsPerPage', '50'));

	const aiProvider = $derived(settingsStore.get('ai.provider', ''));
	const aiModel = $derived(settingsStore.get('ai.model', ''));
	const aiApiKey = $derived(settingsStore.get('ai.apiKey', ''));
	const aiBaseUrl = $derived(settingsStore.get('ai.baseUrl', ''));

	const modelPlaceholders: Record<string, string> = {
		anthropic: 'claude-sonnet-4-20250514',
		openai: 'gpt-4o',
		openrouter: 'anthropic/claude-sonnet-4',
		ollama: 'llama3.2',
		'': 'Select a provider first'
	};
</script>

<Topbar title="Settings" />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mx-auto max-w-2xl space-y-8">
		{#if settingsStore.loading}
			<p class="text-zinc-400">Loading settings...</p>
		{:else}
			<!-- Appearance -->
			<section>
				<h2 class="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">Appearance</h2>
				<div class="space-y-4">
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300">Theme</label>
							<p class="text-xs text-zinc-500">Choose your preferred color scheme</p>
						</div>
						<select
							value={currentTheme}
							onchange={(e) => setTheme(e.currentTarget.value)}
							class="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						>
							<option value="light">Light</option>
							<option value="dark">Dark</option>
						</select>
					</div>
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300">Font size</label>
							<p class="text-xs text-zinc-500">Base font size in pixels</p>
						</div>
						<select
							value={fontSize}
							onchange={(e) => setSetting('appearance.fontSize', e.currentTarget.value)}
							class="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						>
							<option value="12">12</option>
							<option value="14">14</option>
							<option value="16">16</option>
							<option value="18">18</option>
						</select>
					</div>
				</div>
			</section>

			<!-- General -->
			<section>
				<h2 class="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">General</h2>
				<div class="space-y-4">
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300"
								>Default KB</label
							>
							<p class="text-xs text-zinc-500">Knowledge base used when none is specified</p>
						</div>
						<input
							type="text"
							value={defaultKb}
							onchange={(e) => setSetting('general.defaultKb', e.currentTarget.value)}
							placeholder="e.g., my-notes"
							class="w-48 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						/>
					</div>
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300"
								>Items per page</label
							>
							<p class="text-xs text-zinc-500">Default number of entries shown per page</p>
						</div>
						<select
							value={itemsPerPage}
							onchange={(e) => setSetting('general.itemsPerPage', e.currentTarget.value)}
							class="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						>
							<option value="25">25</option>
							<option value="50">50</option>
							<option value="100">100</option>
						</select>
					</div>
				</div>
			</section>

			<!-- AI Provider -->
			<section>
				<h2 class="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">AI Provider</h2>
				<p class="mb-4 text-xs text-zinc-500">
					Configure an LLM provider for AI features: summarize, auto-tag, link suggestions, and
					chat.
				</p>
				<div class="space-y-4">
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300"
								>Provider</label
							>
							<p class="text-xs text-zinc-500">LLM service to use</p>
						</div>
						<select
							value={aiProvider}
							onchange={(e) => {
								setSetting('ai.provider', e.currentTarget.value);
								connectionResult = null;
							}}
							class="w-48 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						>
							<option value="">None</option>
							<option value="anthropic">Anthropic</option>
							<option value="openai">OpenAI</option>
							<option value="openrouter">OpenRouter</option>
							<option value="ollama">Ollama</option>
						</select>
					</div>
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300">Model</label>
							<p class="text-xs text-zinc-500">Model name (leave empty for default)</p>
						</div>
						<input
							type="text"
							value={aiModel}
							onchange={(e) => setSetting('ai.model', e.currentTarget.value)}
							placeholder={modelPlaceholders[aiProvider] ?? modelPlaceholders['']}
							class="w-48 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						/>
					</div>
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300"
								>API Key</label
							>
							<p class="text-xs text-zinc-500">Authentication key for the provider</p>
						</div>
						<input
							type="password"
							value={aiApiKey}
							onchange={(e) => {
								setSetting('ai.apiKey', e.currentTarget.value);
								connectionResult = null;
							}}
							placeholder="sk-..."
							class="w-48 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						/>
					</div>
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300"
								>Base URL</label
							>
							<p class="text-xs text-zinc-500">
								Custom API endpoint (for OpenRouter, Ollama, or self-hosted)
							</p>
						</div>
						<input
							type="text"
							value={aiBaseUrl}
							onchange={(e) => setSetting('ai.baseUrl', e.currentTarget.value)}
							placeholder={aiProvider === 'ollama' ? 'http://localhost:11434/v1' : 'Optional'}
							class="w-48 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						/>
					</div>
					<div class="flex items-center justify-between">
						<div>
							{#if connectionResult}
								<span
									class="text-sm {connectionResult.ok
										? 'text-green-600 dark:text-green-400'
										: 'text-red-500'}"
								>
									{connectionResult.message}
								</span>
							{/if}
						</div>
						<button
							onclick={testAIConnection}
							disabled={testingConnection}
							class="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
						>
							{testingConnection ? 'Testing...' : 'Test Connection'}
						</button>
					</div>
				</div>
			</section>

			{#if settingsStore.error}
				<p class="text-sm text-red-500">{settingsStore.error}</p>
			{/if}
		{/if}
	</div>
</div>
