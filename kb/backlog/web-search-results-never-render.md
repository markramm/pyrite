---
id: web-search-results-never-render
type: backlog_item
title: "Web: search results never render — header says '20 results', list shows skeleton bars forever (API returns data fine)"
kind: bug
status: proposed
priority: high
effort: S
created: "2026-07-03"
tags: [web, search, bug, ux-audit-2026-07]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
---

## Problem

Reproduced on demo.pyrite.wiki 2026-07-03 (1440x900, both via
`/search?q=` navigation and live typing): the results header renders
("20 results") but the result list shows skeleton placeholder bars
permanently (>6s after networkidle). The API is healthy —
`GET /api/search?q=OODA+loop&mode=keyword` returns 20 well-formed
results with `<mark>` highlights, kb_name, entry_type, importance.
Two console 401s fire on page load (possibly related — an
auth-gated request the anonymous demo session can't satisfy blocking
the render path?).

Search is the flagship flow; a first-time user (or invited pilot
peer) hits this within minutes and concludes the product is broken.
Screenshots: scratchpad ux-audit/30-search-results-after-wait.png,
33.

## Fix

Root-cause the render stall (skeleton state never cleared —
suspect: the component awaits a second request that 401s for
anonymous users, or a store update never resolves). Fix, and make
the failure mode honest: if any part of result hydration fails,
show the results we have or an error, never permanent skeletons.
Check whether this reproduces locally with auth (may be
demo/anonymous-specific — which is exactly the pilot peer's
first-session condition).

## Acceptance criteria

- Anonymous demo user sees rendered results.
- e2e search spec asserts result text content (not just container
  presence), gated in CI per [[web-test-confusion-surfaces]].
- Zero console 401s on the search page for a read-authorized user.
