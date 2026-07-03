---
id: web-sidebar-ia-regroup
type: backlog_item
title: "Web: regroup the sidebar — 14 flat nav items spanning 4 scopes, system-vocabulary labels, anonymous KB switcher"
kind: improvement
status: proposed
priority: high
effort: M
created: "2026-07-03"
tags: [web, ux, ia, sidebar, copy, ux-audit-2026-07]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
---

## Problem

`Sidebar.svelte` (247 lines) is navigation rail + tool palette +
status panel at once: 9 stacked sections, and a 14-item FLAT nav
list (:59-74) mixing four scopes with no grouping — content browsing
(Entries, Collections, Tags, Timeline, Daily Notes), analysis
(Graph, Overview, Orient, QA), git workflow (Review queue, Changes,
Merge Queue), and admin (Settings). The order encodes nothing
(structure-is-information failure).

Labels are system vocabulary: "Orient", "QA", and THREE git-flavored
queues (Changes / Review queue / Merge Queue) whose relationship is
documented only in a code comment (`SubmitForReview.svelte:1-8`);
Merge Queue is admin-gated but its two siblings are not, so
non-admin users see two-thirds of a workflow. The KB switcher — the
control that (sometimes) rescopes everything below it — is an
unlabeled native `<select>` (`KBSwitcher.svelte:5-14`). Sections
appear/disappear with auth resolution, recency, and role, so the
panel mutates shape during load.

Live-walkthrough additions (demo, 2026-07-03): "Overview" vs
"Orient" is an undifferentiated twin pair carrying the app's core
mental model (global dashboard vs per-KB dashboard) as two
near-synonyms — and the landing page deepens it by sending "Explore
in app" traffic to /orient while the sidebar highlights Overview.
The sidebar quick-search box sits 40px below the "Search" nav item
and goes to the same place (redundant affordance). The wordmark is
nearly invisible in light mode (see
[[web-light-mode-chrome-repair]]). "QA" reads as
"questions & answers" to a knowledge-tool audience.

## Fix

1. Group nav into 3-4 labeled sections: Browse / Analyze / Review /
   Admin (roughly). Order within groups by frequency of use.
2. User-vocabulary rename pass: "Quality checks" not "QA"; make
   Orient's label say what it does ("KB overview"?); unify the three
   git queues under one "Review" concept with role-aware content.
3. Make the KB switcher visibly consequential: label it, style it as
   the scope control, and visually bind it to the KB-scoped nav
   group (depends on [[web-kb-context-single-authority]] for the
   scoping to actually be true).
4. Reserve space for conditional sections (recent, user menu) so the
   panel doesn't reflow during load.

## Acceptance criteria

- A new user can say what each sidebar item does from its label and
  group (hallway-test 3 people or best judgment).
- Nav items that don't apply to the user's role are hidden as a
  coherent group, not individually.
