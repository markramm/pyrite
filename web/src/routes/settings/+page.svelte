<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import LoadingState from '$lib/components/common/LoadingState.svelte';
	import { uiStore } from '$lib/stores/ui.svelte';
	import { settingsStore } from '$lib/stores/settings.svelte';
	import { api } from '$lib/api/client';
	import { onMount } from 'svelte';

	let testingConnection = $state(false);
	let connectionResult = $state<{ ok: boolean; message: string } | null>(null);
	let exportingKB = $state(false);
	let exportResult = $state<{ ok: boolean; message: string } | null>(null);
	let exportRepoUrl = $state('');
	let exportKbName = $state('');
	let showExportDialog = $state(false);

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
			const result = await api.testAIConnection();
			connectionResult = { ok: result.ok, message: result.message };
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

	const editorMode = $derived(
		typeof window !== 'undefined'
			? (localStorage.getItem('pyrite-editor-mode') ?? 'source')
			: 'source'
	);
	const searchMode = $derived(
		typeof window !== 'undefined'
			? (localStorage.getItem('pyrite-search-mode') ?? 'keyword')
			: 'keyword'
	);

	function setLocalSetting(key: string, value: string) {
		if (typeof window !== 'undefined') {
			localStorage.setItem(key, value);
		}
	}

	const modelPlaceholders: Record<string, string> = {
		anthropic: 'claude-sonnet-4-20250514',
		openai: 'gpt-4o',
		gemini: 'gemini-2.0-flash',
		openrouter: 'anthropic/claude-sonnet-4',
		ollama: 'llama3.2',
		'': 'Select a provider first'
	};

	const providerBaseUrls: Record<string, string> = {
		gemini: 'https://generativelanguage.googleapis.com/v1beta/openai/',
		ollama: 'http://localhost:11434/v1'
	};

	function openExportDialog() {
		exportResult = null;
		exportRepoUrl = '';
		exportKbName = defaultKb || '';
		showExportDialog = true;
	}

	async function handleExportToGitHub() {
		if (!exportKbName || !exportRepoUrl) return;
		exportingKB = true;
		exportResult = null;
		try {
			const result = await api.exportKB(exportKbName, exportRepoUrl);
			exportResult = {
				ok: result.success,
				message: result.message
			};
		} catch (e) {
			exportResult = {
				ok: false,
				message: e instanceof Error ? e.message : 'Export failed'
			};
		} finally {
			exportingKB = false;
		}
	}
</script>

<svelte:head><title>Settings — Pyrite</title></svelte:head>

<Topbar title="Settings" />

<div class="flex-1 overflow-y-auto p-6">
	<div class="mx-auto max-w-2xl space-y-8">
		<h1 class="page-title mb-6 text-2xl font-bold">Settings</h1>
		{#if settingsStore.loading}
			<LoadingState message="Loading settings..." />
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
								const provider = e.currentTarget.value;
								setSetting('ai.provider', provider);
								connectionResult = null;
								// Set or clear base URL based on provider defaults
								const defaultUrl = providerBaseUrls[provider] ?? '';
								const currentUrl = aiBaseUrl;
								// Clear URL if it was a provider default, or set the new default
								const isProviderDefault = Object.values(providerBaseUrls).includes(currentUrl);
								if (defaultUrl || isProviderDefault) {
									setSetting('ai.baseUrl', defaultUrl);
								}
							}}
							class="w-48 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						>
							<option value="">None</option>
							<option value="anthropic">Anthropic</option>
							<option value="openai">OpenAI</option>
							<option value="gemini">Google Gemini</option>
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
							<p class="text-xs text-zinc-500">
								{aiProvider === 'ollama' ? 'Not required for local Ollama' : 'Authentication key for the provider'}
							</p>
						</div>
						<input
							type="password"
							value={aiApiKey}
							onchange={(e) => {
								setSetting('ai.apiKey', e.currentTarget.value);
								connectionResult = null;
							}}
							placeholder={aiProvider === 'ollama' ? 'Not required' : 'sk-...'}
							class="w-48 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						/>
					</div>
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300"
								>Base URL</label
							>
							<p class="text-xs text-zinc-500">
								Custom API endpoint (for Gemini, OpenRouter, Ollama, or self-hosted)
							</p>
						</div>
						<input
							type="text"
							value={aiBaseUrl}
							onchange={(e) => setSetting('ai.baseUrl', e.currentTarget.value)}
							placeholder={providerBaseUrls[aiProvider] ?? 'Optional'}
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

			<!-- Editor -->
			<section>
				<h2 class="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">Editor</h2>
				<div class="space-y-4">
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300"
								>Default editor mode</label
							>
							<p class="text-xs text-zinc-500">How entries open for editing</p>
						</div>
						<select
							value={editorMode}
							onchange={(e) => setLocalSetting('pyrite-editor-mode', e.currentTarget.value)}
							class="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						>
							<option value="source">Source</option>
							<option value="wysiwyg">WYSIWYG</option>
						</select>
					</div>
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300"
								>Default search mode</label
							>
							<p class="text-xs text-zinc-500">Search strategy used when none is specified</p>
						</div>
						<select
							value={searchMode}
							onchange={(e) => setLocalSetting('pyrite-search-mode', e.currentTarget.value)}
							class="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
						>
							<option value="keyword">Keyword</option>
							<option value="semantic">Semantic</option>
							<option value="hybrid">Hybrid</option>
						</select>
					</div>
				</div>
			</section>

			<!-- Data -->
			<section>
				<h2 class="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">Data</h2>
				<div class="space-y-4">
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300">Import</label>
							<p class="text-xs text-zinc-500">Import entries from an external source</p>
						</div>
						<div class="relative group">
							<button
								disabled
								class="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium opacity-50 cursor-not-allowed dark:border-zinc-600"
							>
								Import...
							</button>
							<span
								class="pointer-events-none absolute right-0 top-full mt-1 w-28 rounded bg-zinc-800 px-2 py-1 text-center text-xs text-zinc-100 opacity-0 transition-opacity group-hover:opacity-100"
							>
								Coming soon
							</span>
						</div>
					</div>
					<div class="flex items-center justify-between">
						<div>
							<label class="text-sm font-medium text-zinc-700 dark:text-zinc-300">Export to GitHub</label>
							<p class="text-xs text-zinc-500">Export your knowledge base entries to a GitHub repository</p>
						</div>
						<button
							onclick={openExportDialog}
							class="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
						>
							Export to GitHub...
						</button>
					</div>
					{#if showExportDialog}
						<div class="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-800/50">
							<div class="space-y-3">
								<div>
									<label class="text-xs font-medium text-zinc-600 dark:text-zinc-400">KB Name</label>
									<input
										type="text"
										bind:value={exportKbName}
										placeholder="e.g., my-notes"
										class="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
									/>
								</div>
								<div>
									<label class="text-xs font-medium text-zinc-600 dark:text-zinc-400">GitHub Repo URL</label>
									<input
										type="text"
										bind:value={exportRepoUrl}
										placeholder="https://github.com/user/repo"
										class="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
									/>
								</div>
								<div class="flex items-center gap-2">
									<button
										onclick={handleExportToGitHub}
										disabled={exportingKB || !exportKbName || !exportRepoUrl}
										class="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
									>
										{exportingKB ? 'Exporting...' : 'Export'}
									</button>
									<button
										onclick={() => (showExportDialog = false)}
										class="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
									>
										Cancel
									</button>
								</div>
								{#if exportResult}
									<p class="text-sm {exportResult.ok ? 'text-green-600 dark:text-green-400' : 'text-red-500'}">
										{exportResult.message}
									</p>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</section>

			<!-- Keyboard Shortcuts -->
			<section>
				<h2 class="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100"
					>Keyboard Shortcuts</h2
				>
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm font-medium text-zinc-700 dark:text-zinc-300"
							>View all keyboard shortcuts</p
						>
						<p class="text-xs text-zinc-500">Press <kbd
								class="rounded border border-zinc-300 bg-zinc-100 px-1 py-0.5 font-mono text-xs dark:border-zinc-600 dark:bg-zinc-800"
								>?</kbd
							> anywhere to open</p>
					</div>
					<button
						onclick={() => {
							if (typeof window !== 'undefined') {
								window.dispatchEvent(new KeyboardEvent('keydown', { key: '?' }));
							}
						}}
						class="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
					>
						View shortcuts
					</button>
				</div>
			</section>

			<!-- More Settings -->
			<section>
				<h2 class="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">More</h2>
				<div class="space-y-2">
					<a
						href="/settings/api-keys"
						class="flex items-center justify-between rounded-md border border-zinc-300 px-4 py-3 text-sm hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
					>
						<span>My API Keys</span>
						<span class="text-zinc-400">&rarr;</span>
					</a>
					<a
						href="/settings/kbs"
						class="flex items-center justify-between rounded-md border border-zinc-300 px-4 py-3 text-sm hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
					>
						<span>Knowledge Bases</span>
						<span class="text-zinc-400">&rarr;</span>
					</a>
					<a
						href="/settings/users"
						class="flex items-center justify-between rounded-md border border-zinc-300 px-4 py-3 text-sm hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
					>
						<span>Users & Permissions</span>
						<span class="text-zinc-400">&rarr;</span>
					</a>
					<a
						href="/settings/index"
						class="flex items-center justify-between rounded-md border border-zinc-300 px-4 py-3 text-sm hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
					>
						<span>Index Management</span>
						<span class="text-zinc-400">&rarr;</span>
					</a>
					<a
						href="/settings/plugins"
						class="flex items-center justify-between rounded-md border border-zinc-300 px-4 py-3 text-sm hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
					>
						<span>Plugins</span>
						<span class="text-zinc-400">&rarr;</span>
					</a>
				</div>
			</section>

			{#if settingsStore.error}
				<p class="text-sm text-red-500">{settingsStore.error}</p>
			{/if}
		{/if}
	</div>
</div>
