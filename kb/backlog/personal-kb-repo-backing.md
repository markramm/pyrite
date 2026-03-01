---
id: personal-kb-repo-backing
title: "Git-Backed Personal KBs and Usage Tiers"
type: backlog_item
tags:
- feature
- web-ui
- auth
- git
kind: feature
priority: high
effort: L
status: planned
links:
- per-kb-permissions
- oauth-providers
- demo-site-deployment
- roadmap
---

## Problem

Ephemeral KBs (#112) give demo site visitors a sandbox, but it expires. Users who invest time building a KB want to keep it. The natural upgrade path: connect a GitHub repo to make it persistent. The server operator also needs configurable resource limits to manage a multi-user deployment responsibly.

## Solution

### Personal KB Lifecycle

```
Visitor (anonymous)
  └─ reads curated demo KBs

Registered user (GitHub OAuth)
  └─ creates ephemeral sandbox (configurable TTL)
  └─ connects a public GitHub repo → personal KB becomes permanent
     - Pyrite clones repo, indexes it, user gets admin on their KB
     - Changes sync back to GitHub (push on save or manual commit)
     - KB survives across sessions — it's their repo
```

### Connect Repo Flow

1. User has an ephemeral KB (or starts fresh)
2. Clicks "Connect GitHub Repo" in KB settings
3. Selects a public repo from their GitHub account (OAuth scope: `public_repo`)
4. Backend clones repo into workspace, discovers KB structure
5. If repo has `kb.yaml` → imports as-is; if empty → initializes with user's ephemeral KB content
6. Ephemeral KB is replaced with the repo-backed KB (same name, new path)
7. `KBConfig.ephemeral` set to `False`, `remote` set to repo URL
8. `kb_permission` entry preserved (user stays admin)

### Usage Tiers (configurable resource limits)

The server operator configures resource limits per usage tier. This is pure infrastructure — how the operator assigns tiers to users (manually, via webhook, via future billing integration) is their concern.

```python
@dataclass
class UsageTierConfig:
    """Resource limits for a usage tier. Configured per deployment."""
    max_personal_kbs: int = 1
    max_entries_per_kb: int = 500
    max_storage_mb: int = 50
    allow_private_repos: bool = False
    allow_persistent_non_git: bool = False
    rate_limit_read: str = "100/minute"
    rate_limit_write: str = "30/minute"
```

```yaml
# config.yaml
auth:
  usage_tiers:
    default:
      max_personal_kbs: 1
      max_entries_per_kb: 500
      max_storage_mb: 50
      allow_private_repos: false
      allow_persistent_non_git: false
    elevated:
      max_personal_kbs: 5
      max_entries_per_kb: 10000
      max_storage_mb: 500
      allow_private_repos: true
      allow_persistent_non_git: true
      rate_limit_read: "500/minute"
      rate_limit_write: "100/minute"
```

The `local_user` table gets a `usage_tier` column (default: `"default"`). The operator assigns tiers however they choose.

When `usage_tiers` is not configured (local dev, self-hosted), no limits are enforced — everything works as today.

### Data Model Changes

Migration (combined with earlier auth migrations if not yet shipped):

```sql
ALTER TABLE local_user ADD COLUMN usage_tier TEXT DEFAULT 'default';
```

`KBConfig` additions:
```python
owner_id: int | None = None   # local_user.id of the KB owner
```

### What This Does NOT Include

- Billing/payment integration (operator's concern)
- GitHub App installation (uses user's OAuth token for repo access)
- Multi-tenant isolation (all KBs share one SQLite DB — fine for demo, revisit for scale)

## Files

| File | Action | Summary |
|------|--------|---------|
| `pyrite/config.py` | Edit | Add `UsageTierConfig`, `usage_tiers` to `AuthConfig`, `owner_id` to `KBConfig` |
| `pyrite/storage/migrations.py` | Edit | Add `usage_tier` column to `local_user` |
| `pyrite/services/auth_service.py` | Edit | Add usage-tier-aware limit checks |
| `pyrite/services/kb_service.py` | Edit | `connect_repo_to_kb()` — clone, replace ephemeral, set remote |
| `pyrite/server/endpoints/admin.py` | Edit | New endpoint: `POST /api/kbs/{name}/connect-repo` |
| `pyrite/server/auth_endpoints.py` | Edit | Expose usage tier info in `/auth/me` |
| `web/src/routes/login/+page.svelte` | Edit | Post-login redirect shows personal KB or sandbox |
| `web/src/lib/components/KBSettings.svelte` | Edit | "Connect GitHub Repo" button |
| `tests/test_personal_kb.py` | Create | Repo connection, usage tier limits, ephemeral-to-permanent upgrade |

## Prerequisites

- OAuth providers (#110) — needs GitHub OAuth for repo access
- Per-KB permissions (#112) — ownership model for personal KBs

## Success Criteria

- GitHub user signs in, creates sandbox, connects public repo, KB persists
- Ephemeral KB content migrates to repo-backed KB seamlessly
- Usage tier limits enforced when configured (entry count, storage, number of KBs)
- Operator can define usage tiers in config without code changes
- No limits enforced when `usage_tiers` not configured (local dev, self-hosted)

## Launch Context

Ships after OAuth (#110) and per-KB permissions (#112). Core demo site feature — "try Pyrite, then connect your repo to keep your work."
