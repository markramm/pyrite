<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth.svelte';
	import { onMount } from 'svelte';

	let username = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let displayName = $state('');
	let error = $state<string | null>(null);
	let submitting = $state(false);

	onMount(() => {
		if (!authStore.authConfig.allow_registration) {
			goto('/login');
		}
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = null;

		if (password !== confirmPassword) {
			error = 'Passwords do not match';
			return;
		}

		if (password.length < 8) {
			error = 'Password must be at least 8 characters';
			return;
		}

		submitting = true;
		try {
			await authStore.register(username, password, displayName || undefined);
			goto('/');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Registration failed';
		} finally {
			submitting = false;
		}
	}
</script>

<div class="flex min-h-screen items-center justify-center bg-zinc-900">
	<div class="w-full max-w-sm space-y-6 px-4">
		<div class="text-center">
			<h1 class="font-display text-3xl text-gold-400">Pyrite</h1>
			<p class="mt-2 text-sm text-zinc-400">Create your account</p>
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
				<label for="display-name" class="block text-sm font-medium text-zinc-300">Display Name <span class="text-zinc-500">(optional)</span></label>
				<input
					id="display-name"
					type="text"
					bind:value={displayName}
					autocomplete="name"
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
					minlength={8}
					autocomplete="new-password"
					class="mt-1 block w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-zinc-100 placeholder-zinc-500 focus:border-gold-500 focus:outline-none focus:ring-1 focus:ring-gold-500"
				/>
			</div>

			<div>
				<label for="confirm-password" class="block text-sm font-medium text-zinc-300">Confirm Password</label>
				<input
					id="confirm-password"
					type="password"
					bind:value={confirmPassword}
					required
					autocomplete="new-password"
					class="mt-1 block w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-zinc-100 placeholder-zinc-500 focus:border-gold-500 focus:outline-none focus:ring-1 focus:ring-gold-500"
				/>
			</div>

			<button
				type="submit"
				disabled={submitting}
				class="w-full rounded bg-gold-500 px-4 py-2 font-medium text-zinc-900 hover:bg-gold-400 disabled:opacity-50"
			>
				{submitting ? 'Creating account...' : 'Create account'}
			</button>
		</form>

		<p class="text-center text-sm text-zinc-400">
			Already have an account? <a href="/login" class="text-gold-400 hover:text-gold-300">Sign in</a>
		</p>
	</div>
</div>
