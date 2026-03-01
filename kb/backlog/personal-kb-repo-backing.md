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
effort: M
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
  └─ exports ephemeral KB entries to a GitHub repo → permanent personal KB
     - User selects a public repo or forks a curated KB
     - Pyrite exports markdown files, commits, and pushes
     - Repo can be mounted as a regular KB on any Pyrite instance
     - Ephemeral KB cleaned up on its normal TTL
```

### Two Flows: Export and Fork

#### Flow A: Export to New Repo

For users who built entries in their ephemeral sandbox and want to keep them:

1. User has an ephemeral KB with entries they want to keep
2. Clicks "Export to GitHub Repo" in KB settings
3. Selects an existing public repo from their GitHub account (OAuth scope: `public_repo`)
4. Backend clones repo, exports ephemeral KB entries as markdown files into the checkout
5. If repo already has `kb.yaml` → entries conform to existing schema; if empty → exports `kb.yaml` + entries
6. Backend commits and pushes to the repo (or presents a PR for user review)
7. Ephemeral KB remains until TTL expiry — no in-place swap needed
8. User can mount the repo as a regular KB on their own Pyrite instance, or submit to the awesome-list for demo site inclusion

#### Flow B: Fork a Curated KB

For users who want to contribute to or build on an existing curated KB:

1. User browses a curated KB on the demo site
2. Clicks "Fork & Edit" on the KB or on a specific entry
3. Pyrite forks the upstream repo to the user's GitHub account (OAuth scope: `public_repo`)
4. The fork becomes a personal KB the user can edit freely in their ephemeral sandbox
5. When ready, the user clicks "Submit PR" — Pyrite creates a pull request from their fork to the upstream repo
6. The upstream maintainer reviews via normal GitHub PR flow (CODEOWNERS, CI checks, `pyrite ci` validation)

**Side benefit:** curated KBs accumulate GitHub forks from contributors — visible social proof of community engagement. A KB with 50 forks tells a stronger story than one with 50 stars.

This maps directly onto how open source already works. Contributors don't need write access to the upstream KB — Layer 1 (git) handles the entire contribution model through fork/PR. No per-KB write permissions needed on curated KBs.

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

### What This Does NOT Include

- Billing/payment integration (operator's concern)
- GitHub App installation (uses user's OAuth token for repo access)
- In-place ephemeral-to-permanent KB swap (export is simpler and avoids state migration complexity)
- Multi-tenant isolation (all KBs share one SQLite DB — fine for demo, revisit for scale)

## Files

| File | Action | Summary |
|------|--------|---------|
| `pyrite/config.py` | Edit | Add `UsageTierConfig`, `usage_tiers` to `AuthConfig` |
| `pyrite/storage/migrations.py` | Edit | Add `usage_tier` column to `local_user` |
| `pyrite/services/auth_service.py` | Edit | Add usage-tier-aware limit checks |
| `pyrite/services/kb_service.py` | Edit | `export_kb_to_repo()` and `fork_kb_repo()` — export/fork, commit/push, create PR |
| `pyrite/server/endpoints/admin.py` | Edit | New endpoints: `POST /api/kbs/{name}/export-to-repo`, `POST /api/kbs/{name}/fork` |
| `pyrite/server/auth_endpoints.py` | Edit | Expose usage tier info in `/auth/me` |
| `web/src/lib/components/KBSettings.svelte` | Edit | "Export to GitHub Repo" and "Fork & Edit" buttons |
| `tests/test_personal_kb.py` | Create | Export flow, fork flow, PR creation, usage tier limits |

## OAuth Scope Note

Initial GitHub OAuth login uses `read:user,read:org` (no repo access). When the user clicks "Export to GitHub Repo," a separate OAuth authorization request with `public_repo` scope is triggered. This avoids asking for write access to all public repos at initial sign-in — scope escalation happens only when the user explicitly wants it.

## Prerequisites

- OAuth providers (#110) — needs GitHub OAuth for repo access
- Per-KB permissions (#112) — ephemeral KB sandbox support

## Success Criteria

- **Export flow:** GitHub user signs in, creates sandbox, exports entries to public repo
- **Fork flow:** GitHub user forks a curated KB, edits in their sandbox, submits PR to upstream
- Exported/forked entries are valid markdown files that any Pyrite instance can mount
- PRs from forks include `pyrite ci` validation results (when CI is configured on upstream)
- Usage tier limits enforced when configured (entry count, storage, number of KBs)
- Operator can define usage tiers in config without code changes
- No limits enforced when `usage_tiers` not configured (local dev, self-hosted)

## Launch Context

Ships after OAuth (#110) and per-KB permissions (#112). Core demo site feature — "try Pyrite, then fork a KB or export your sandbox to keep your work." The fork model also drives community engagement: curated KBs accumulate GitHub forks from contributors, providing visible social proof and a familiar open-source contribution workflow.
