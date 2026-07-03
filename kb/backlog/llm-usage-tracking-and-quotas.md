---
id: llm-usage-tracking-and-quotas
type: backlog_item
title: "Per-user LLM usage tracking and quota enforcement at LLMService layer"
kind: feature
status: proposed
priority: medium
effort: M
tags: [ai, llm, quotas, cost, hosting]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
---

## Problem

`pyrite/services/llm_service.py` makes provider calls without recording
token usage, cost, or which user initiated the request. The
quota_service exists for general usage quotas but is not wired into the LLM
path.

Consequences for the hosted instance:

- No way to enforce a "10 chat turns per day" limit on the free tier.
- No way to see which user is burning tokens.
- No way to bill back costs per investigation team.
- BYOK works (users supply their own keys), but for the platform-supplied
  key path there's no governance at all.

## Solution

1. In `LLMService.complete()` / `.stream()`, after the provider call,
   record:
   - User ID (from the call context — already plumbed through for BYOK
     routing)
   - Provider, model, request kind (chat / qa / summarize / embed)
   - Input tokens, output tokens, cache-read tokens, cache-creation
     tokens
   - Estimated cost (per-model rates in a config table)
   - Timestamp
2. Store in a new SQLite table (`llm_usage`) on the engagement tier (per
   ADR-0003).
3. Add `QuotaService.check_llm_quota(user_id, kind)` and call it
   pre-request. Return a clear error when over quota.
4. Expose:
   - `GET /api/usage/me` — current user's usage in the current window
   - `GET /api/admin/usage` — admin view across users
   - CLI: `pyrite usage --me` and `pyrite admin usage`
5. Defaults: no quota (off) for self-hosted; admin sets per-tier limits.

## Acceptance criteria

- Every LLM call records a usage row.
- Cost estimates use a model→price config (versioned, easy to update).
- Quota check fires before the provider call and returns a useful error.
- Admin endpoint shows per-user totals.
- Tests cover: usage record creation, quota enforcement (over and under),
  cost estimation arithmetic, cache-token tracking.

## Related

- `llm-prompt-caching` — caching tokens need to be tracked separately
  (they're cheap but not free)
- `quota-service` — extend the existing service rather than build new
- `epic-pyrite-publication-strategy` — hosted instance needs this
