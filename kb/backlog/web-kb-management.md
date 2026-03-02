---
id: web-kb-management
title: "Web UI KB Management"
type: backlog_item
tags:
- feature
- web-ui
- kb
kind: feature
priority: high
effort: M
status: proposed
links:
- per-kb-permissions
- personal-kb-repo-backing
- roadmap
---

## Problem

Knowledge bases are currently defined in `config.yaml` and managed exclusively via the CLI (`pyrite kb add`, `pyrite kb remove`, `pyrite kb list`). The `GET /api/kbs` endpoint reads the KB list from config, and the web UI's `KBSwitcher` component consumes it — but there's no way to add, remove, or configure KBs from the web UI. This blocks two planned features:

1. **Per-KB permissions** ([[per-kb-permissions]]): Admins need a UI to grant/revoke per-KB access for users. The permissions model is designed but has no management surface beyond future API calls.

2. **Fork & push workflow** ([[personal-kb-repo-backing]]): Users need to connect GitHub repos, fork curated KBs, and manage their personal KBs — all from the browser. There's no web surface for any of this.

Without a KB management UI, both features would require CLI access, which defeats the purpose of the web-first experience for demo site visitors and team members.

## Solution

### Architecture Note: Config vs. Database

Today KBs are defined in `config.yaml` and loaded at startup. The CLI mutates this file. For web UI management, we need a runtime API that can modify the KB list. Two approaches:

1. **Config-file mutation via API**: API endpoints read/write `config.yaml` directly (same as CLI does). Simple, preserves single source of truth, but has concurrency concerns and requires file system access.
2. **DB-backed KB registry**: Move KB definitions from config to the SQLite database. Config provides initial/default KBs, DB holds runtime additions. More robust for multi-user, required for per-KB permissions anyway.

Recommended: **Approach 2** for multi-user deployments (demo site, teams). Config KBs are "system KBs" that can't be removed via UI. User-added KBs live in the DB. This aligns with the per-KB permissions model which already needs a `kb_permission` table referencing KB names.

For local/single-user mode, config-only continues to work — the DB registry layer is additive.

### KB Management Page

Add a `/settings/kbs` route (nested under settings) with:

- **KB list**: All KBs the current user can see (config-defined + DB-registered, filtered by per-KB permissions when available). Shows name, type, entry count, path, indexed status, source (config vs. user-added).
- **Add KB**: Form to register an existing directory or git repo as a KB. Fields: name, path, type (auto-detected from `kb.yaml`). Writes to DB, not config.
- **Remove KB**: Remove a user-added KB from the registry (does not delete files). Config-defined KBs cannot be removed via UI. Confirmation dialog.
- **KB detail panel**: Click a KB to see/edit its configuration — default role, description, entry types, index health.
- **Re-index**: Trigger `index sync` for a specific KB from the UI.

### Admin Controls (when per-KB permissions ships)

Extend the KB detail panel with:

- **Access control**: List users with explicit grants on this KB. Add/remove grants. Show effective role resolution (explicit grant > KB default > global role).
- **Default role**: Set the KB's `default_role` (public read, private, etc.).
- **Ephemeral KB management**: For admins — list active ephemeral KBs, force-expire, adjust limits.

### Personal KB Controls (when repo backing ships)

Add to the user's KB detail view:

- **Connect repo**: OAuth flow to link a GitHub repo as the backing store.
- **Fork KB**: Fork a curated KB to user's GitHub account.
- **Submit PR**: Create a PR from user's fork to the upstream curated KB.
- **Export**: Export ephemeral KB entries to a connected repo.

### REST API Endpoints

Several endpoints already exist (`GET /api/kbs`). New endpoints needed:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/kbs` | Register a new KB |
| `DELETE` | `/api/kbs/{name}` | Remove a KB from index |
| `PUT` | `/api/kbs/{name}` | Update KB configuration |
| `POST` | `/api/kbs/{name}/reindex` | Trigger index sync for a KB |
| `GET` | `/api/kbs/{name}/health` | Index health for a specific KB |

Per-KB permission endpoints (ships with [[per-kb-permissions]]):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/kbs/{name}/permissions` | List access grants |
| `POST` | `/api/kbs/{name}/permissions` | Grant access |
| `DELETE` | `/api/kbs/{name}/permissions/{user_id}` | Revoke access |

## Files

| File | Action | Summary |
|------|--------|---------|
| `pyrite/server/endpoints/kbs.py` | Create | KB CRUD + reindex + health endpoints |
| `pyrite/server/schemas.py` | Edit | Add `CreateKBRequest`, `UpdateKBRequest` schemas |
| `pyrite/server/endpoints/__init__.py` | Edit | Register KB router |
| `web/src/routes/settings/kbs/+page.svelte` | Create | KB management page |
| `web/src/lib/api/client.ts` | Edit | Add KB management API methods |
| `web/src/lib/components/layout/Sidebar.svelte` | Edit | Add link to KB settings (or nest under existing Settings nav) |
| `tests/test_kb_endpoints.py` | Create | KB CRUD endpoint tests |

## Phased Delivery

1. **Phase 1** (this item): KB list, add, remove, reindex, health. Read-only config view. No auth integration.
2. **Phase 2** (with [[per-kb-permissions]]): Access control panel, default role editing, permission grants.
3. **Phase 3** (with [[personal-kb-repo-backing]]): GitHub repo connection, fork, export, PR submission.

## Prerequisites

- REST API KB list endpoint (exists: `GET /api/kbs`)
- Settings page infrastructure (exists: `/settings` route)

## Success Criteria

- Admin can add/remove KBs from the web UI without CLI
- Admin can trigger reindex and see index health per-KB
- KB detail shows configuration, entry count, type, path
- Settings page links to KB management
- Works with auth disabled (local dev) and auth enabled (demo/team)
