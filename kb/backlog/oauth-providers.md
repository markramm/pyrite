---
id: oauth-providers
title: "OAuth Provider Authentication (GitHub, Google)"
type: backlog_item
tags:
- feature
- web-ui
- auth
- security
- oauth
kind: feature
priority: high
effort: L
status: planned
links:
- web-ui-auth
- demo-site-deployment
- roadmap
---

## Problem

Phase 1 auth (#94) added local username/password authentication. But most users already have GitHub or Google accounts and expect "Sign in with GitHub" — especially developers evaluating Pyrite. Requiring yet another username/password creates friction and password fatigue.

OAuth also enables:

- **Org-based access control** — GitHub org membership maps to tiers (e.g., `my-org` members get write, everyone else gets read)
- **Zero-password deployments** — demo site can offer GitHub login without managing passwords
- **Account linking** — users who registered locally can link their GitHub/Google identity later
- **Avatar + display name** — pulled from the provider, better UX out of the box

## Solution

### Phase 1: GitHub OAuth (high value, low friction)

GitHub is the natural fit — Pyrite already has `GitHubAuth` config, a `user` table with `github_login`/`github_id`, and the target audience is developers.

**OAuth flow:**
1. Frontend redirects to `GET /auth/github` which returns a GitHub authorize URL
2. GitHub redirects back to `GET /auth/github/callback?code=...`
3. Backend exchanges code for access token, fetches user profile
4. Creates or links `local_user` record, creates session, sets cookie
5. Redirects to frontend with session established

**Data model changes:**

Migration v7 adds `auth_provider` column to `local_user`:

```sql
ALTER TABLE local_user ADD COLUMN auth_provider TEXT DEFAULT 'local';
ALTER TABLE local_user ADD COLUMN provider_id TEXT;
ALTER TABLE local_user ADD COLUMN avatar_url TEXT;
-- Make password_hash nullable (OAuth users don't have passwords)
-- SQLite doesn't support ALTER COLUMN, so this is handled at the application layer
```

Unique constraint: `(auth_provider, provider_id)` — one GitHub account maps to one local_user.

**Account linking:** If a user with `username=alice` (local) logs in via GitHub and their GitHub username is also `alice`, offer to link the accounts. If different usernames, create a new account.

**Org-based tier mapping (config):**

```yaml
auth:
  enabled: true
  providers:
    github:
      client_id: "..."
      client_secret: "..."
      allowed_orgs: [my-org]          # Optional: restrict to org members
      org_tier_map:                    # Optional: org -> tier
        my-org: write
        my-org/admins-team: admin
      default_tier: read              # Tier for authenticated users not in org map
    google:
      client_id: "..."
      client_secret: "..."
      allowed_domains: [mycompany.com]
      default_tier: read
```

**Dependencies:** `httpx` (already in server deps) for token exchange.

### Phase 2: Google OAuth

Same flow, different provider URLs and profile API. Google OAuth is useful for:
- Corporate teams using Google Workspace
- Non-developer users who don't have GitHub accounts

**Scopes:** `openid email profile` — standard OIDC.

### Phase 3: Generic OIDC (future)

Abstract the provider interface so any OIDC-compliant provider works (Keycloak, Auth0, Okta, Azure AD). This is the corporate SSO story.

## Design Decisions

### Provider abstraction

```python
class OAuthProvider(Protocol):
    name: str
    def get_authorize_url(self, state: str, redirect_uri: str) -> str: ...
    def exchange_code(self, code: str, redirect_uri: str) -> OAuthToken: ...
    def get_user_profile(self, token: OAuthToken) -> OAuthProfile: ...

@dataclass
class OAuthProfile:
    provider: str       # "github", "google"
    provider_id: str    # GitHub user ID, Google sub
    username: str       # GitHub login, Google email prefix
    display_name: str
    email: str | None
    avatar_url: str | None
    orgs: list[str]     # GitHub orgs, Google domain
```

This keeps the auth_service clean — it receives an `OAuthProfile` and handles user creation/linking/session creation.

### CSRF protection for OAuth

The `state` parameter in the OAuth flow must be:
1. Generated server-side (random token)
2. Stored in a short-lived cookie or DB
3. Verified on callback to prevent CSRF

### Reuse of existing GitHubAuth config

The existing `GitHubAuth` dataclass in config.py is for repository access (private repo cloning). OAuth login is a different concern — different client ID, different scopes (`read:user,read:org` vs `repo`), different callback URL. Keep them separate in config to avoid confusion.

### Session reuse

OAuth login produces the same session token as local login. The `verify_session` path is identical — no changes needed in `verify_api_key` or the API middleware.

## Files

| File | Action | Phase | Summary |
|------|--------|-------|---------|
| `pyrite/config.py` | Edit | 1 | Add `OAuthProviderConfig` and `providers` to `AuthConfig` |
| `pyrite/storage/migrations.py` | Edit | 1 | Migration v7: add `auth_provider`, `provider_id`, `avatar_url` to `local_user` |
| `pyrite/storage/models.py` | Edit | 1 | Add columns to `LocalUser` model |
| `pyrite/services/oauth_providers.py` | Create | 1 | `GitHubOAuth`, `GoogleOAuth` provider implementations |
| `pyrite/services/auth_service.py` | Edit | 1 | Add `oauth_login(profile)`, `link_account(user_id, profile)` methods |
| `pyrite/server/auth_endpoints.py` | Edit | 1 | Add `/auth/github`, `/auth/github/callback`, `/auth/google`, `/auth/google/callback` |
| `web/src/lib/types/auth.ts` | Edit | 1 | Add `providers` to `AuthConfig`, `OAuthProvider` type |
| `web/src/lib/stores/auth.svelte.ts` | Edit | 1 | No major changes (cookie-based, same session flow) |
| `web/src/routes/login/+page.svelte` | Edit | 1 | Add "Sign in with GitHub" / "Sign in with Google" buttons |
| `tests/test_oauth_providers.py` | Create | 1 | Unit tests for provider implementations (mocked HTTP) |
| `tests/test_auth_endpoints.py` | Edit | 1 | Add OAuth callback tests |

## Frontend Changes

Login page gets provider buttons above the local login form:

```
  ┌──────────────────────────────────┐
  │            Pyrite                 │
  │   Sign in to your account        │
  │                                  │
  │  [  Sign in with GitHub  ]       │
  │  [  Sign in with Google  ]       │
  │                                  │
  │  ──────── or ────────            │
  │                                  │
  │  Username: [_______________]     │
  │  Password: [_______________]     │
  │           [ Sign in ]            │
  │                                  │
  │  No account? Register            │
  └──────────────────────────────────┘
```

Provider buttons only appear when that provider is configured. When only OAuth is configured (no local), the form is hidden.

`/auth/config` response adds:
```json
{
  "enabled": true,
  "allow_registration": true,
  "providers": ["github", "google"]
}
```

## Prerequisites

- Web UI auth Phase 1 (done, #94)

## Success Criteria

- GitHub OAuth: click "Sign in with GitHub" -> authorize -> redirected to Pyrite, logged in
- Google OAuth: same flow with Google
- Account linking: local user can link GitHub after the fact
- Org mapping: GitHub org members get configured tier
- All existing local auth continues to work
- OAuth users appear in `/auth/me` with avatar_url
- No new external dependencies beyond httpx (already present)

## Launch Context

Phase 1 (GitHub) ships as part of 0.12 Public Demo track — it makes the demo site much more accessible. Phase 2 (Google) follows quickly since the provider abstraction is already in place. Phase 3 (generic OIDC) is post-launch for corporate adoption.
