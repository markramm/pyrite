---
id: wire-user-usage-tier-resolution-for-quota-enforcement
title: Wire user usage-tier resolution for quota enforcement
type: backlog_item
tags:
- quotas
- auth
- tech-debt
importance: 5
kind: task
status: done
priority: medium
effort: S
rank: 0
---

## Problem

QuotaService has 3 check methods (check_kb_creation_allowed,
check_entry_creation_allowed, and the new check_llm_quota) that all
take a user_tier parameter (e.g. "free", "pro"), matched against
config.settings.auth.usage_tiers. Investigated while wiring
check_llm_quota into a live request path
(llm-usage-tracking-and-quotas): there is no source of truth anywhere
that maps a user to one of these tier names.

local_user.role is an auth-permission tier (read/write/admin) -- a
completely different axis from a resource/billing tier
(free/pro/enterprise). No column, no lookup table, no admin-set field
connects them.

Confirmed via a repo-wide grep for `QuotaService(`: there are ZERO
call sites in production code for any of the three check methods --
QuotaService has existed as fully dead/unwired code since it was
extracted from KBService.

## Resolution

1. Usage tier lives on `local_user.usage_tier` (TEXT, default
   "default") -- this column already existed since migration v10 and
   was already ORM-mapped, but nothing read or wrote it. No new
   migration was needed.
2. `AuthService.get_user()` now includes `usage_tier` in its SELECT;
   new `AuthService.set_usage_tier(user_id, tier)` method added
   (unvalidated against a fixed enum -- matched against
   `config.settings.auth.usage_tiers` at check time, same as before).
   4 new tests in `tests/test_auth_service.py::TestUsageTier`.
3. Wired `QuotaService.check_llm_quota` into all 4 AI endpoints via a
   new `_enforce_llm_quota()` helper in `ai_ep.py`:
   - `ai_summarize` (kind="summarize")
   - `ai_auto_tag` (kind="auto-tag")
   - `ai_suggest_links` (kind="suggest-links")
   - `ai_chat` NOT wired -- it calls `llm.stream()`, which has no
     usage-recording path at all yet (only `.complete()` does). Chat
     quota enforcement needs stream-side usage recording first;
     tracked as a new follow-up rather than guessed at here.
4. Fixed a real bug found via this wiring: `LLMService.complete()` had
   no `kind` parameter, so `_record_anthropic_usage()` always recorded
   `kind="chat"` regardless of caller -- a per-kind quota check (e.g.
   `kind="summarize"`) could never see its own usage rows and would
   never trigger. Added `kind: str = "chat"` param to `complete()`,
   threaded through `_anthropic_complete()` to
   `_record_anthropic_usage()`. Default preserves existing behavior
   for callers that don't pass it. Tests in
   `tests/test_llm_service.py::TestLLMServiceUsageTracking`.
5. Self-hosted / no-usage_tiers-configured behavior unchanged:
   `_enforce_llm_quota` no-ops for anonymous requests and
   `QuotaService.check_llm_quota` already fails open on missing
   config/tier/limit.

## Explicitly deferred (out of scope for this ticket)

`check_kb_creation_allowed` and `check_entry_creation_allowed` were
NOT wired. Investigated the only plausible call site (`POST
/kbs/ephemeral` -> `AuthService.create_user_ephemeral_kb()`) and found
it uses an entirely separate, older limiting system
(`ephemeral_min_tier`/`ephemeral_max_per_user` on `AuthConfig`), not
`UsageTierConfig.max_personal_kbs`/`max_entries_per_kb`. There is no
existing endpoint whose semantics match what these two methods check.
Wiring them would mean inventing new functionality (e.g. a
general-purpose "create personal KB" endpoint), which is a real
design/product decision, not a follow-up to this fix. Filed as a new
ticket: quota-wire-kb-and-entry-creation-checks.

## Acceptance criteria

- [x] A user's usage tier is resolvable from their user_id via a real
  data source (not guessed/hardcoded).
- [x] check_llm_quota is called from all real LLM request paths that
  currently support usage recording (summarize/auto-tag/suggest-links).
  ai_chat deferred, see above and new follow-up ticket.
- [ ] check_kb_creation_allowed / check_entry_creation_allowed --
  deferred, see quota-wire-kb-and-entry-creation-checks.
- [x] Self-hosted (auth disabled or no usage_tiers configured) remains
  fully unlimited -- verified via existing QuotaService fail-open
  tests plus new endpoint-level tests in test_ai_quota_enforcement.py.
