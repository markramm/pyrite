---
id: wire-kb-entry-creation-quota-checks-or-remove-dead-quotaservice-methods
title: Wire KB/entry creation quota checks or remove dead QuotaService methods
type: backlog_item
tags:
- auth
- tech-debt
- quotas
importance: 5
kind: task
status: proposed
priority: medium
effort: M
rank: 0
---

## Problem

QuotaService.check_kb_creation_allowed and check_entry_creation_allowed
remain unwired -- zero call sites in production code. Investigated
while closing wire-user-usage-tier-resolution-for-quota-enforcement:
the only plausible existing call site for KB-creation limits, `POST
/kbs/ephemeral` -> AuthService.create_user_ephemeral_kb(), uses a
completely separate, older limiting system
(AuthConfig.ephemeral_min_tier / ephemeral_max_per_user), not
UsageTierConfig.max_personal_kbs / max_entries_per_kb. There is no
existing endpoint whose semantics match what these two QuotaService
methods actually check.

## Fix

Needs a real product decision, not a guess -- pick one:

1. Design and build the endpoint(s) these checks are meant to gate
   (e.g. a general-purpose "create personal KB" flow distinct from
   the ephemeral-KB flow), then wire check_kb_creation_allowed /
   check_entry_creation_allowed into them.
2. Decide the ephemeral-KB system IS the intended enforcement point,
   and either migrate it onto UsageTierConfig (retiring
   ephemeral_min_tier/ephemeral_max_per_user) or update these two
   QuotaService methods' semantics to match the ephemeral system.
3. Conclude they're speculative/unneeded and delete them from
   QuotaService, along with their tests, rather than carrying
   permanently-dead code.

## Acceptance criteria

- Either both methods are called from at least one real request path,
  or they (and their now-orphaned config fields, if any) are removed.
- No regression to the self-hosted fail-open-on-no-config behavior.
