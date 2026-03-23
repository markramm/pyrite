/** Authentication types for the Pyrite web UI. */

export interface AuthUser {
	id: number;
	username: string;
	display_name: string | null;
	role: 'read' | 'write' | 'admin';
	auth_provider: string;
	avatar_url: string | null;
	kb_permissions: Record<string, string>;
}

export interface AuthConfig {
	enabled: boolean;
	allow_registration: boolean;
	providers: string[];
	anonymous_tier: string;
}

export interface LoginRequest {
	username: string;
	password: string;
}

export interface RegisterRequest {
	username: string;
	password: string;
	display_name?: string;
}
