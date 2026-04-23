/** Auth store using Svelte 5 runes */

import { api } from '$lib/api/client';
import type { AuthConfig, AuthUser } from '$lib/types/auth';

class AuthStore {
	user = $state<AuthUser | null>(null);
	authConfig = $state<AuthConfig>({ enabled: false, allow_registration: false, require_invite_code: false, providers: [], anonymous_tier: 'none' });
	loading = $state(true);
	error = $state<string | null>(null);

	get isAuthenticated(): boolean {
		return this.user !== null;
	}

	get isAdmin(): boolean {
		return this.user?.role === 'admin';
	}

	get allowsAnonymous(): boolean {
		return this.authConfig.anonymous_tier !== 'none';
	}

	async init() {
		this.loading = true;
		try {
			this.authConfig = await api.getAuthConfig();
			if (this.authConfig.enabled) {
				try {
					this.user = await api.getMe();
				} catch {
					// Not authenticated — anonymous user, leave user as null
					this.user = null;
				}
			}
		} catch {
			// Auth config endpoint not available — auth is disabled
			this.authConfig = {
				enabled: false,
				allow_registration: false,
				require_invite_code: false,
				providers: [],
				anonymous_tier: 'none'
			};
		} finally {
			this.loading = false;
		}
	}

	async login(username: string, password: string) {
		this.error = null;
		try {
			this.user = await api.login(username, password);
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Login failed';
			throw e;
		}
	}

	async register(username: string, password: string, display_name?: string, invite_code?: string) {
		this.error = null;
		try {
			this.user = await api.register(username, password, display_name, invite_code);
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Registration failed';
			throw e;
		}
	}

	async logout() {
		try {
			await api.logout();
		} catch {
			// Ignore errors — clear local state anyway
		}
		this.user = null;
	}
}

export const authStore = new AuthStore();
