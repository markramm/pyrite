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
status: proposed
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
extracted from KBService. This is not new breakage from the LLM
quota work; it's a pre-existing gap the LLM work simply surfaced by
being the first attempt to actually call one of these methods from a
live endpoint.

## Fix

Needs a real design decision, not a guess:

1. Decide where a user's usage tier lives -- most likely a new
   `local_user.usage_tier` column (default e.g. "free"), set at
   registration and admin-editable, distinct from `role`.
2. Wire it into the 3 existing QuotaService call sites that need it:
   - KB creation (pyrite_kb_service or wherever `pyrite kb create`/
     the REST create-KB path lives)
   - Entry creation (per-KB entry count check)
   - LLM requests (ai_ep.py's summarize/auto-tag/suggest-links/chat
     endpoints, via QuotaService.check_llm_quota)
3. Decide default tier behavior for self-hosted (no auth, or auth
   without usage_tiers configured) -- almost certainly "unlimited",
   matching every check method's existing fail-open-on-no-config
   convention.

## Acceptance criteria

- A user's usage tier is resolvable from their user_id via a real
  data source (not guessed/hardcoded).
- All 3 QuotaService check methods are called from at least one real
  request path each.
- Self-hosted (auth disabled or no usage_tiers configured) remains
  fully unlimited -- no regression for the common case.
