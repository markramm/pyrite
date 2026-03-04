import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	api: {
		getAuthConfig: vi.fn(),
		getMe: vi.fn(),
		login: vi.fn(),
		register: vi.fn(),
		logout: vi.fn()
	}
}));

import { api } from '$lib/api/client';
import { authStore } from './auth.svelte';

const mockGetAuthConfig = vi.mocked(api.getAuthConfig);
const mockGetMe = vi.mocked(api.getMe);
const mockLogin = vi.mocked(api.login);
const mockRegister = vi.mocked(api.register);
const mockLogout = vi.mocked(api.logout);

const sampleUser = {
	id: 'user-1',
	username: 'alice',
	display_name: 'Alice',
	role: 'user' as const
};

const adminUser = {
	id: 'user-2',
	username: 'admin',
	display_name: 'Admin',
	role: 'admin' as const
};

beforeEach(() => {
	vi.clearAllMocks();
	authStore.user = null;
	authStore.authConfig = { enabled: false, allow_registration: false, providers: [] };
	authStore.loading = true;
	authStore.error = null;
});

describe('AuthStore', () => {
	describe('init', () => {
		it('sets authConfig from API and loads user when auth enabled', async () => {
			const config = { enabled: true, allow_registration: true, providers: ['local'] };
			mockGetAuthConfig.mockResolvedValueOnce(config);
			mockGetMe.mockResolvedValueOnce(sampleUser);

			await authStore.init();
			expect(authStore.authConfig).toEqual(config);
			expect(authStore.user).toEqual(sampleUser);
		});

		it('does not load user when auth is disabled', async () => {
			mockGetAuthConfig.mockResolvedValueOnce({
				enabled: false,
				allow_registration: false,
				providers: []
			});

			await authStore.init();
			expect(mockGetMe).not.toHaveBeenCalled();
			expect(authStore.user).toBeNull();
		});

		it('sets authConfig to disabled defaults when API throws', async () => {
			mockGetAuthConfig.mockRejectedValueOnce(new Error('Network error'));

			await authStore.init();
			expect(authStore.authConfig).toEqual({
				enabled: false,
				allow_registration: false,
				providers: []
			});
			expect(authStore.loading).toBe(false);
		});

		it('sets loading true during init and false after', async () => {
			mockGetAuthConfig.mockImplementation(async () => {
				expect(authStore.loading).toBe(true);
				return { enabled: false, allow_registration: false, providers: [] };
			});

			await authStore.init();
			expect(authStore.loading).toBe(false);
		});
	});

	describe('login', () => {
		it('sets user from API response', async () => {
			mockLogin.mockResolvedValueOnce(sampleUser);

			await authStore.login('alice', 'password123');
			expect(authStore.user).toEqual(sampleUser);
			expect(mockLogin).toHaveBeenCalledWith('alice', 'password123');
		});

		it('sets error message and re-throws on failure', async () => {
			mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'));

			await expect(authStore.login('alice', 'wrong')).rejects.toThrow('Invalid credentials');
			expect(authStore.error).toBe('Invalid credentials');
		});

		it('clears previous error before attempt', async () => {
			authStore.error = 'Previous error';
			mockLogin.mockResolvedValueOnce(sampleUser);

			await authStore.login('alice', 'password123');
			expect(authStore.error).toBeNull();
		});
	});

	describe('register', () => {
		it('sets user from API response', async () => {
			mockRegister.mockResolvedValueOnce(sampleUser);

			await authStore.register('alice', 'password123', 'Alice');
			expect(authStore.user).toEqual(sampleUser);
			expect(mockRegister).toHaveBeenCalledWith('alice', 'password123', 'Alice');
		});

		it('sets error message and re-throws on failure', async () => {
			mockRegister.mockRejectedValueOnce(new Error('Username taken'));

			await expect(authStore.register('alice', 'pass')).rejects.toThrow('Username taken');
			expect(authStore.error).toBe('Username taken');
		});
	});

	describe('logout', () => {
		it('calls api.logout and clears user', async () => {
			authStore.user = sampleUser;
			mockLogout.mockResolvedValueOnce(undefined);

			await authStore.logout();
			expect(mockLogout).toHaveBeenCalled();
			expect(authStore.user).toBeNull();
		});

		it('clears user even if api.logout throws', async () => {
			authStore.user = sampleUser;
			mockLogout.mockRejectedValueOnce(new Error('Network error'));

			await authStore.logout();
			expect(authStore.user).toBeNull();
		});
	});

	describe('isAuthenticated / isAdmin', () => {
		it('derives isAuthenticated and isAdmin from user state', () => {
			expect(authStore.isAuthenticated).toBe(false);
			expect(authStore.isAdmin).toBe(false);

			authStore.user = sampleUser;
			expect(authStore.isAuthenticated).toBe(true);
			expect(authStore.isAdmin).toBe(false);

			authStore.user = adminUser;
			expect(authStore.isAuthenticated).toBe(true);
			expect(authStore.isAdmin).toBe(true);

			authStore.user = null;
			expect(authStore.isAuthenticated).toBe(false);
			expect(authStore.isAdmin).toBe(false);
		});
	});
});
