---
id: llm-usage-tracking-and-quotas
title: "Per-user LLM usage tracking and quota enforcement at LLMService layer"
type: backlog_item
tags: [ai, llm, quotas, cost, hosting]
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
importance: 5
kind: feature
status: proposed
priority: medium
effort: M
rank: 0
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

## Progress

- [x] **`llm_usage` table added** (2026-07-04) — migration v23 in
  `pyrite/storage/migrations.py`, following the v22 (`oauth_state`)
  pattern: plain `CREATE TABLE IF NOT EXISTS`, no ORM model needed.
  Columns: `user_id` (nullable — anonymous/stub access still records),
  `provider`, `model`, `kind` (default `'chat'`), `input_tokens`,
  `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`,
  `estimated_cost_usd`, `created_at`. Indexed on `(user_id, created_at)`
  for the quota-window query.
- [x] **New `LLMUsageService`** (2026-07-04,
  `pyrite/services/llm_usage_service.py`) — `record_usage()`,
  `get_usage(user_id)` (single-user totals), `get_all_usage()`
  (per-user totals, admin view), `check_quota(user_id, kind,
  daily_limit)` (rolling 24h window via `datetime('now', '-1 day')`,
  scoped per `kind` so hitting a chat quota doesn't block summarize
  requests). Cost estimation via a `PRICING` dict (model → per-million-
  token input/output rates) — unpriced models cost `$0` rather than
  raising, matching the ticket's "cost estimates use a model→price
  config, easy to update" criterion. 15 tests, all passing.
- [x] **`LLMService` wired to record usage** (2026-07-04) —
  `__init__` gained optional `usage_service`/`user_id` params (default
  `None`, so every existing caller that doesn't pass them keeps working
  unchanged — verified with a dedicated regression test). `_anthropic_complete`
  calls a new `_record_anthropic_usage()` helper after the provider
  call, reading `response.usage` (the same object already used for the
  existing cache-hit-rate log line) — reuses real data already present
  at the call site, no new provider API surface needed.
  `with_user_key()` (the BYOK override path) carries `usage_service`/
  `user_id` forward into the new instance it returns — verified with a
  dedicated test, since forgetting this would have silently stopped
  tracking the moment a user supplied their own key. **Scoped to
  Anthropic only in this pass** — `_openai_complete` (OpenAI/OpenRouter/
  Ollama/Gemini, all via the OpenAI-compatible SDK) is not yet wired;
  its response shape needs a similar usage-extraction path but wasn't
  done here to keep the change reviewable. Streaming (`.stream()`) also
  not wired — token counts for streamed responses aren't available the
  same way (need end-of-stream accounting), separate follow-up.
- [x] **REST endpoints** (2026-07-04) — `GET /api/usage/me` (any
  authenticated user, or the anonymous/null-user bucket when auth is
  disabled) and `GET /api/admin/usage` (admin-tier gated, per-user
  totals) in `pyrite/server/endpoints/admin.py`. `get_llm_service`'s DI
  factory now resolves `request.state.auth_user` and constructs the
  `LLMUsageService` + passes `user_id`, so every REST-surface LLM call
  (chat, summarize, auto-tag, suggest-links — anything going through
  `get_llm_service`) is tracked automatically, no per-endpoint changes
  needed beyond the DI factory. 2 new endpoint tests, both passing.
- [x] **MCP wired, without per-user attribution** (2026-07-04) —
  `PyriteMCPServer.qa_svc`'s `LLMService` construction now passes a
  `usage_service`, but `user_id=None` — MCP has no per-request user
  identity in the current architecture (server-wide tier, not per-user
  auth), so this gives platform-key cost VISIBILITY without per-user
  ATTRIBUTION. Wiring real per-user MCP attribution would need a
  larger architectural change (MCP session-level auth) explicitly out
  of scope for this pass.
- [ ] **CLI usage command NOT wired** (`pyrite usage --me` /
  `pyrite admin usage`) — the CLI's usage model doesn't map cleanly:
  it's a local single-user tool with no "current logged-in user"
  concept the way the REST/web layer has (`request.state.auth_user`).
  A CLI usage command would need to either accept an explicit
  `--user-id` (awkward, and not how any other CLI command works) or
  report the DB-wide totals unconditionally (which `get_all_usage()`
  already supports and could back a `pyrite usage --all` command
  fairly easily) — deferred rather than force a design decision in
  this pass.
- [ ] **`QuotaService.check_llm_quota()` NOT added** — `check_quota()`
  already exists on the new `LLMUsageService` (arguably the more
  natural home, since it needs the usage table this service owns) but
  the ticket specifically asks for it on the existing `QuotaService`
  (currently pure config-driven, no DB dependency at all). Not wired
  as a pre-request gate anywhere yet — no endpoint currently calls
  `check_quota()` before dispatching to the LLM. This is the most
  load-bearing remaining piece (recording without enforcing means the
  data exists but nothing is actually gated) and the natural next
  step, deliberately left for a follow-up rather than bolted on
  without deciding where the check belongs (per-endpoint in
  `ai_ep.py`? A shared dependency? What are sane default daily
  limits per tier?).

## Acceptance criteria

- Every LLM call records a usage row. **Partially met** — every
  Anthropic `complete()` call through the REST layer (and MCP QA
  assessment) records a row. OpenAI-compatible providers and streaming
  calls do not yet.
- Cost estimates use a model→price config (versioned, easy to
  update). **Met** — `PRICING` dict in `llm_usage_service.py`.
- Quota check fires before the provider call and returns a useful
  error. **Not met** — `check_quota()` exists but isn't called from
  any request path yet.
- Admin endpoint shows per-user totals. **Met** —
  `GET /api/admin/usage`.
- Tests cover: usage record creation, quota enforcement (over and
  under), cost estimation arithmetic, cache-token tracking. **Met** —
  15 service-level tests + 2 endpoint tests + 3 LLMService-integration
  tests cover all four areas named.

## Related

- `llm-prompt-caching` — caching tokens need to be tracked separately
  (they're cheap but not free)
- `quota-service` — extend the existing service rather than build new
- `epic-pyrite-publication-strategy` — hosted instance needs this
