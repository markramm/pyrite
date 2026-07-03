---
id: web-daily-notes-view-side-effect
type: backlog_item
title: "Web: visiting Daily Notes silently creates today's entry — navigation with a write side effect"
kind: bug
status: proposed
priority: high
effort: S
created: "2026-07-03"
tags: [web, daily-notes, data-integrity, ux-audit-2026-07]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
---

## Problem

Observed live on the demo 2026-07-03 during a READ-ONLY audit:
merely navigating to Daily Notes auto-created "Daily Note -
2026-07-03" in the `guide` KB — Total Entries went 4796 → 4797 and
the note appeared in Recent Entries ("1m ago") without any edit
action. Viewing a date creates data.

Why it matters beyond surprise: (a) GET-with-side-effects violates
the read/write tier model — a read-tier peer on the shared instance
could apparently create entries by browsing; (b) it pollutes the
corpus and git history with empty notes for every date anyone looks
at; (c) count drift erodes trust ("why did the entry count change?
I didn't do anything").

## Fix

Daily Notes for a date with no note renders an empty state with an
explicit "Start today's note" action; creation happens on that
action (or on first keystroke in an editor), never on navigation.
Purge/ignore empty auto-created notes in counts. Verify the create
goes through the write-permission check (a read-only user must get
the empty state, not a created file).

## Acceptance criteria

- Navigating to any Daily Notes date performs zero writes.
- A read-tier user browsing Daily Notes triggers no permission
  errors and no entries.
