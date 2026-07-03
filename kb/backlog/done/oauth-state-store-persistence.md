---
id: oauth-state-store-persistence
title: "Persist OAuth CSRF state across process restarts and replicas"
type: backlog_item
tags: [security, oauth, hosting, multi-process]
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
importance: 5
kind: improvement
status: done
priority: high
effort: S
rank: 0
---

> Re-prioritized low → high 2026-07-02: prerequisite for the
> trusted-peer read-only pilot ([[epic-shared-instance-readiness]]) —
> a login failure in a peer's first session is a trust-killer.

## Problem

GitHub OAuth state tokens are kept in an in-memory dict on the auth
service. Two failure modes:

1. **Process restart during login.** User clicks "Sign in with GitHub",
   gets redirected, comes back with the state token — process restarted in
   the meantime, state is gone, login fails with a confusing error.
2. **Multi-replica deploys.** If `investigate.transparencycascade.org`
   ever runs behind a load balancer with more than one worker, the state
   created on replica A and returned to replica B is invalid.

Today the single-process self-host case works fine. The hosted instance
plan in `epic-pyrite-publication-strategy` makes (1) more visible and
opens the door to (2).

## Solution

Move OAuth state to the SQLite database with a short TTL (5 min, matching
the current in-memory TTL). One table: `oauth_state` with `state` (PK),
`user_intent`, `created_at`. Cleanup on read + a periodic sweep.

This is intentionally minimal — Redis is overkill for this volume and
adds an operational dependency.

## Acceptance criteria

- OAuth state survives a process restart.
- TTL still enforced (stale tokens rejected).
- No change to single-process behavior in self-host.
- Tests for the new store: insert/get/expire/cleanup.

## Out of scope

- Migrating to a different OAuth flow.
- Distributed-replica session store (separate concern — `oauth-providers`
  is done, this just hardens state storage).

## Related

- `oauth-providers` (done)
- `epic-pyrite-publication-strategy` — hosted instance context
