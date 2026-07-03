---
id: web-test-confusion-surfaces
type: backlog_item
title: "Web: test the confusion surfaces — KB precedence, Sidebar, graph; promote e2e into CI"
kind: tech_debt
status: proposed
priority: medium
effort: M
created: "2026-07-03"
tags: [web, testing, ux-audit-2026-07]
links:
- target: ci-make-green-and-load-bearing
  relation: related
  kb: pyrite
- target: web-kb-context-single-authority
  relation: related
  kb: pyrite
---

## Problem

The frontend suite (47 files, ~496 tests) covers stores, the API
client, and utils well — and covers NONE of the surfaces where the
reported UX problems live: no tests for Sidebar, KBSwitcher, Topbar,
GraphView/GraphControls, CommentsPanel, SubmitForReview, or ANY
route page. The KB-precedence logic (`urlKB ?? kbStore.activeKB`)
exists only inline in pages, untested. 11 Playwright e2e specs exist
(`e2e/graph.spec.ts`, `search`, `entry-crud`, …) but e2e is not a
passing/gating CI job, so the only enforced coverage is logic that
was never the problem.

## Fix

1. Extract KB-precedence resolution to one util (part of
   [[web-kb-context-single-authority]]) and unit-test the
   URL/store/default/persistence matrix.
2. Component tests for Sidebar (per role/auth/KB state — the
   conditional-rendering matrix) and KBSwitcher (navigates, doesn't
   dead-zone).
3. Promote the existing e2e specs into CI as a gating job once
   [[ci-make-green-and-load-bearing]] lands; add one light-mode
   visual pass (see [[web-light-mode-chrome-repair]]).

## Acceptance criteria

- The switcher dead-zone bug class
  ([[web-kb-context-single-authority]]) is regression-locked.
- e2e runs green in CI on every push affecting web/.
