---
id: per-kb-permissions
title: "Per-KB Permissions and Ephemeral KB Access Control"
type: backlog_item
tags:
- feature
- web-ui
- auth
- security
- permissions
kind: feature
priority: high
effort: L
status: planned
links:
- web-ui-auth
- oauth-providers
- demo-site-deployment
- roadmap
---

## Problem

The current auth system (#94) has a single global role per user (`read`/`write`/`admin`). This doesn't support three real deployment scenarios:

1. **Demo site**: Visitors read curated KBs. Registered users get a private sandbox (ephemeral KB) to try editing. Admins manage curated content. A `write` user shouldn't be able to edit the curated demo KBs.

2. **Teams**: Alice has `admin` on `ops-kb` but only `read` on `research-kb`. Bob has `write` on both. Currently impossible — one role applies to everything.

3. **Personal + shared**: A user's private KB is invisible to others, while shared KBs are readable by the team.

Additionally, ephemeral KB creation currently requires `admin` tier, which means the demo site can't let normal users create sandboxes.

## Solution

### Per-KB ACL Table

New `kb_permission` table that maps `(user_id, kb_name) -> role`:

```sql
CREATE TABLE kb_permission (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES local_user(id) ON DELETE CASCADE,
    kb_name TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'read', 'write', 'admin'
    granted_by INTEGER REFERENCES local_user(id),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, kb_name)
);
```

### Permission Resolution

```
effective_role(user, kb) =
    1. kb_permission[user_id, kb_name]   -- explicit per-KB grant
    2. ?? kb.default_role                -- KB-level default (e.g., "read" for public KBs)
    3. ?? user.role                      -- user's global role fallback
    4. ?? anonymous_tier                 -- anonymous fallback (if no user)
```

This preserves all current behavior: if no `kb_permission` rows exist and no `default_role` is set on the KB, the global user role applies — exactly as today.

### KB Visibility

Add `default_role` to `KBConfig`:

```python
@dataclass
class KBConfig:
    ...
    default_role: str | None = None  # None = use user's global role. "read" = public. "none" = private.
```

| `default_role` | Behavior |
|----------------|----------|
| `None` | Current behavior — user's global role applies |
| `"read"` | Anyone can read, writing needs explicit grant or global write+ |
| `"write"` | Anyone can read/write |
| `"none"` | Private — only users with explicit `kb_permission` entries can access |

### Ephemeral KB Access Control

Extend `AuthConfig` for ephemeral KB policy:

```python
@dataclass
class AuthConfig:
    ...
    # Ephemeral KB policy
    ephemeral_min_tier: str = "write"       # Minimum global tier to create ephemeral KBs
    ephemeral_max_per_user: int = 1         # Max active ephemeral KBs per user
    ephemeral_default_ttl: int = 86400      # Default TTL in seconds (24h)
    ephemeral_max_ttl: int = 604800         # Maximum allowed TTL (7d)
```

When a user creates an ephemeral KB:
1. Check user has `>= ephemeral_min_tier` globally
2. Check user hasn't exceeded `ephemeral_max_per_user`
3. Create KB with `default_role="none"` (private)
4. Auto-insert `kb_permission(user_id, kb_name, role="admin")`
5. Creator can now do anything in their sandbox; nobody else can see it

### Deployment Profiles

**Local dev** (auth disabled):
- No changes. Everything works as today — implicit admin on all KBs.

**Demo site**:
```yaml
auth:
  enabled: true
  anonymous_tier: read
  allow_registration: true
  ephemeral_min_tier: read       # Even read-tier users can create a sandbox
  ephemeral_max_per_user: 1
  ephemeral_default_ttl: 86400   # 24 hours
  ephemeral_max_ttl: 86400
```
- Anonymous: reads curated KBs (global `anonymous_tier: read`)
- Registered user: reads curated KBs (global role `read`) + creates one private ephemeral KB (auto-admin on it)
- Registered user (GitHub): can connect a public repo to make KB permanent (see [[personal-kb-repo-backing]])
- Admin: manages curated KBs (global role `admin`)

**Team**:
```yaml
auth:
  enabled: true
  ephemeral_min_tier: write
  ephemeral_max_per_user: 3
  ephemeral_default_ttl: 2592000  # 30 days
```
- KBs have `default_role` set individually:
  - `docs-kb`: `default_role: read` (everyone reads, write-tier edits)
  - `private-research`: `default_role: none` (only granted users)
- Per-user grants via `kb_permission` for fine-grained access

## Implementation

### DB Migration (v8)

```sql
-- Per-KB permissions
CREATE TABLE kb_permission (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES local_user(id) ON DELETE CASCADE,
    kb_name TEXT NOT NULL,
    role TEXT NOT NULL,
    granted_by INTEGER REFERENCES local_user(id),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, kb_name)
);
CREATE INDEX idx_kb_permission_user ON kb_permission(user_id);
CREATE INDEX idx_kb_permission_kb ON kb_permission(kb_name);

-- Track ephemeral KB ownership
ALTER TABLE local_user ADD COLUMN ephemeral_kb_count INTEGER DEFAULT 0;
```

### AuthService Extensions

```python
class AuthService:
    ...
    def get_kb_role(self, user_id: int | None, kb_name: str) -> str | None:
        """Resolve effective role for user on a specific KB."""

    def grant_kb_permission(self, user_id: int, kb_name: str, role: str, granted_by: int) -> None:
        """Grant per-KB permission."""

    def revoke_kb_permission(self, user_id: int, kb_name: str) -> bool:
        """Remove per-KB permission grant."""

    def list_kb_permissions(self, kb_name: str) -> list[dict]:
        """List all permission grants for a KB."""

    def create_user_ephemeral_kb(self, user_id: int, name: str | None = None) -> dict:
        """Create ephemeral KB owned by user, with access control."""
```

### Endpoint Changes

**New middleware**: Replace `requires_tier(tier)` with `requires_kb_tier(tier)` for KB-scoped endpoints. This checks per-KB ACL instead of (or in addition to) global role:

```python
def requires_kb_tier(tier: str):
    """Check user has sufficient permission on the target KB."""
    async def _check(request: Request, kb: str = Query(None)):
        # Resolve KB name from query param, path param, or request body
        effective_role = auth_service.get_kb_role(user_id, kb_name)
        if TIER_LEVELS.get(effective_role, -1) < TIER_LEVELS.get(tier, 99):
            raise HTTPException(403, ...)
    return _check
```

Non-KB-scoped endpoints (health, settings, stats) continue using `requires_tier`.

**Ephemeral KB endpoint** — change from admin-only to respecting `ephemeral_min_tier`:

```python
@router.post("/kbs/ephemeral")
async def create_ephemeral_kb(request: Request, ...):
    """Create a personal ephemeral KB for the authenticated user."""
```

### Files

| File | Action | Summary |
|------|--------|---------|
| `pyrite/config.py` | Edit | Add ephemeral policy fields to `AuthConfig`, add `default_role` to `KBConfig` |
| `pyrite/storage/migrations.py` | Edit | Migration v8: `kb_permission` table |
| `pyrite/storage/models.py` | Edit | Add `KBPermission` model |
| `pyrite/services/auth_service.py` | Edit | Add `get_kb_role`, `grant_kb_permission`, `create_user_ephemeral_kb` |
| `pyrite/server/api.py` | Edit | Add `requires_kb_tier` dependency |
| `pyrite/server/endpoints/admin.py` | Edit | Ephemeral KB endpoint uses new policy |
| `pyrite/server/endpoints/entries.py` | Edit | Use `requires_kb_tier` for write operations |
| `pyrite/server/auth_endpoints.py` | Edit | Expose KB permissions in `/auth/me` |
| `web/src/lib/types/auth.ts` | Edit | Add KB permissions to `AuthUser` |
| `tests/test_kb_permissions.py` | Create | Permission resolution, ACL CRUD, ephemeral limits |
| `tests/test_auth_endpoints.py` | Edit | Ephemeral KB creation tests |

## Prerequisites

- Web UI auth Phase 1 (#94) -- done
- Ideally after OAuth (#110) so OAuth users can also create ephemeral KBs, but not blocking

## Success Criteria

- Demo site: anonymous reads curated KBs, registered user creates private sandbox, admin manages curated content
- Team: different users have different access levels on different KBs
- Ephemeral KBs: configurable limits, auto-ownership, private by default
- All existing behavior preserved when no `kb_permission` rows exist and no `default_role` set
- Global admin can still override everything (admin on all KBs regardless of ACL)

## Launch Context

Ships as part of 0.12 Public Demo track. Required before demo site deployment (#85) for the sandbox feature. The per-KB ACL also enables team deployments in 0.13+.
