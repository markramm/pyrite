<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { authStore } from '$lib/stores/auth.svelte';
	import { brandStore } from '$lib/stores/brand.svelte';

	let username = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let submitting = $state(false);

	// Check for OAuth error in query params
	const oauthError = page.url.searchParams.get('error');
	if (oauthError === 'oauth_failed') {
		error = 'GitHub sign-in failed. Please try again.';
	}

	const hasGitHub = $derived(authStore.authConfig.providers.includes('github'));

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = null;
		submitting = true;
		try {
			await authStore.login(username, password);
			goto('/');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Login failed';
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Login — {brandStore.name}</title></svelte:head>

<div class="flex min-h-screen items-center justify-center bg-zinc-900">
	<div class="w-full max-w-sm space-y-6 px-4">
		<div class="text-center">
			{#if brandStore.wordmark_url}
				<img
					src={brandStore.wordmark_url}
					alt={brandStore.name}
					class="mx-auto h-10"
					class:brand-invert-on-dark={brandStore.invert_on_dark}
				/>
			{:else}
				<h1 class="font-display text-3xl" style="color: var(--brand-primary)">{brandStore.name}</h1>
			{/if}
			<p class="mt-2 text-sm text-zinc-400">Sign in to your account</p>
		</div>

		{#if error}
			<div class="rounded border border-red-800 bg-red-900/30 px-3 py-2 text-sm text-red-300">
				{error}
			</div>
		{/if}

		{#if hasGitHub}
			<a
				href="/auth/github"
				class="flex w-full items-center justify-center gap-2 rounded border border-zinc-600 bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-100 hover:bg-zinc-700"
			>
				<svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
					<path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
				</svg>
				Sign in with GitHub
			</a>

			<div class="flex items-center gap-3">
				<div class="h-px flex-1 bg-zinc-700"></div>
				<span class="text-xs text-zinc-500">or</span>
				<div class="h-px flex-1 bg-zinc-700"></div>
			</div>
		{/if}

		<form onsubmit={handleSubmit} class="space-y-4">
			<div>
				<label for="username" class="block text-sm font-medium text-zinc-300">Username</label>
				<input
					id="username"
					type="text"
					bind:value={username}
					required
					autocomplete="username"
					class="mt-1 block w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-zinc-100 placeholder-zinc-500 focus:border-gold-500 focus:outline-none focus:ring-1 focus:ring-gold-500"
				/>
			</div>

			<div>
				<label for="password" class="block text-sm font-medium text-zinc-300">Password</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					required
					autocomplete="current-password"
					class="mt-1 block w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-zinc-100 placeholder-zinc-500 focus:border-gold-500 focus:outline-none focus:ring-1 focus:ring-gold-500"
				/>
			</div>

			<button
				type="submit"
				disabled={submitting}
				class="w-full rounded bg-gold-500 px-4 py-2 font-medium text-zinc-900 hover:bg-gold-400 disabled:opacity-50"
			>
				{submitting ? 'Signing in...' : 'Sign in'}
			</button>
		</form>

		{#if authStore.authConfig.allow_registration}
			<p class="text-center text-sm text-zinc-400">
				No account? <a href="/register" class="text-gold-400 hover:text-gold-300">Register</a>
			</p>
		{/if}
	</div>
</div>
