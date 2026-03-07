---
id: auth-service
title: Auth Service
type: component
kind: service
path: pyrite/services/auth_service.py
owner: core
dependencies:
- pyrite.storage
- bcrypt
tags:
- core
- service
- auth
---

Local username/password authentication with session tokens for the web UI. Uses bcrypt for password hashing and SHA-256 hashed opaque tokens for sessions. Supports per-KB permissions via the `kb_permission` table and ephemeral KB access control.

## Key Methods

### User & Session Management

- `register(username, password)` — creates a new user, returns user dict
- `login(username, password)` — validates credentials, creates session token
- `oauth_login(profile, provider_config)` — create/update OAuth user, returns session
- `logout(token)` — invalidates a session
- `verify_session(token)` — returns user info if token is valid

### GitHub Token Management

- `store_github_token(user_id, token, scopes)` — store GitHub OAuth token for a user (scope escalation)
- `get_github_token_for_user(user_id)` — returns `(token, scopes)` tuple; `(None, None)` if not stored
- `clear_github_token(user_id)` — remove stored GitHub token; returns `True` if user found

### Per-KB Permissions

- `get_kb_role(user_id, kb_name, kb_default_role)` — resolve effective role via: global admin → explicit grant → KB default_role → user global role → anonymous tier
- `grant_kb_permission(user_id, kb_name, role, granted_by)` — INSERT OR REPLACE per-KB grant
- `revoke_kb_permission(user_id, kb_name)` — remove per-KB grant
- `list_kb_permissions(kb_name)` — all grants for a KB
- `get_user_kb_permissions(user_id)` — all grants for a user (used by `/auth/me`)
- `create_user_ephemeral_kb(user_id, kb_service, name)` — create ephemeral KB with policy checks (min tier, max per user), auto-grants creator admin

## Permission Resolution Chain

```
effective_role(user, kb) =
    1. Global admin → always "admin"
    2. kb_permission[user_id, kb_name]   -- explicit per-KB grant
    3. kb.default_role                   -- KB-level default
    4. user.role                         -- user's global role fallback
    5. anonymous_tier                    -- anonymous fallback (if no user)
```

## REST Endpoints

Mounted at `/auth` (outside `/api` prefix) via `auth_endpoints.py`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create new user |
| `/auth/login` | POST | Login, returns session token |
| `/auth/logout` | POST | Invalidate session |
| `/auth/me` | GET | Session introspection (includes `kb_permissions`) |
| `/auth/config` | GET | Public auth configuration |
| `/auth/github` | GET | Start GitHub OAuth flow |
| `/auth/github/callback` | GET | GitHub OAuth callback |
| `/auth/github/connect` | GET | Scope escalation: re-auth with `public_repo` scope (requires login) |
| `/auth/github/status` | GET | GitHub connection status (connected, scopes, github_configured) |
| `/auth/github/connect` | DELETE | Disconnect GitHub (clear stored token) |

KB permission management endpoints live under `/api/kbs/{name}/permissions` (see [[rest-api]]).

## Related

- [[rest-api]] — auth endpoints at root, KB permission endpoints under /api
- [[web-frontend]] — web UI consumes auth endpoints
- [[per-kb-permissions]] — design doc for per-KB ACL system
- [[configuration-system]] — `AuthConfig` ephemeral policy fields, `KBConfig.default_role`
