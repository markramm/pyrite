/** Authentication types for the Pyrite web UI. */

export interface AuthUser {
	id: number;
	username: string;
	display_name: string | null;
	role: 'read' | 'write' | 'admin';
}

export interface AuthConfig {
	enabled: boolean;
	allow_registration: boolean;
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
