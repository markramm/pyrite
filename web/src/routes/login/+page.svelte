<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth.svelte';

	let username = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let submitting = $state(false);

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

<div class="flex min-h-screen items-center justify-center bg-zinc-900">
	<div class="w-full max-w-sm space-y-6 px-4">
		<div class="text-center">
			<h1 class="font-display text-3xl text-gold-400">Pyrite</h1>
			<p class="mt-2 text-sm text-zinc-400">Sign in to your account</p>
		</div>

		<form onsubmit={handleSubmit} class="space-y-4">
			{#if error}
				<div class="rounded border border-red-800 bg-red-900/30 px-3 py-2 text-sm text-red-300">
					{error}
				</div>
			{/if}

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
