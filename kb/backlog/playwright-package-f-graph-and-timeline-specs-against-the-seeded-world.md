---
id: playwright-package-f-graph-and-timeline-specs-against-the-seeded-world
title: 'Playwright package F: graph and timeline specs against the seeded world'
type: backlog_item
tags:
- testing
- e2e
- web
- playwright
importance: 5
kind: task
status: in_progress
priority: high
assignee: agent:pyrite-worker
effort: M
rank: 0
---

## Problem

`web/e2e/graph.spec.ts` and `web/e2e/timeline.spec.ts` still assert on visible
text and on "some data or an empty state" rather than on the world Package A
seeded (`web/e2e/fixtures.ts`). Runner evidence for the class: `text=` locators
resolve to two elements the moment a page gains a second element with the same
words; `.first()` hides the strict-mode violation instead of naming the element.

- graph.spec: 6 `text=` locators including `text=Knowledge Graph` and the
  `\d+ nodes, \d+ edges` regex; two `.first()` hops that reach outside the
  package's own pages.
- timeline.spec: `text=/\d+ events/`, `text=No timeline events found`.

## Groom 2026-09-18 (architect, tick 6 — theme 6B)

Acceptance: the ticket's B–G block (assert on seeded data; roles/`href`s/
`data-testid` not text; `data-testid` in the component only where no role
exists; 5x green; zero `text=`; no `.first()` dodges).

Touches: `web/e2e/graph.spec.ts`, `web/e2e/timeline.spec.ts`; only if no role
exists: `web/src/routes/graph/+page.svelte`,
`web/src/lib/components/GraphView.svelte`, `web/src/routes/timeline/+page.svelte`.

Sequence: after A.1 (#118/#138, landed 10:12Z); parallel with G. Cold read: no.
heavy: yes (Playwright).

Out of scope: package A's files (`global-setup.ts`, `fixtures.ts`, `ports.ts`,
`playwright.config.ts` — report a missing seed, do not edit it); the `e2e` CI
job (H); #117; #49 (skip a `toHaveTitle` with a comment naming #49).

## Acceptance

- [ ] Both specs assert on seeded data from `fixtures.ts` — the seeded people,
      events and their links are what the graph and the timeline show — never
      on "a list or an empty state".
- [ ] Zero `text=` locators; no `.first()` used to dodge a strict-mode
      violation. `data-testid` added to a component only where no role or
      `href` identifies the element, and named in the report.
- [ ] Both pass 5x in a row against A's world, using this worktree's derived
      ports (`node web/e2e/print-ports.ts <repo-root>`).
- [ ] A real product bug found by a now-real assertion is reported (GitHub
      issue) and marked `test.fixme` with the bug named, never papered over.
- [ ] Package A's files are not edited; a missing seed is reported.

Part of
[[playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap]],
Package F. 0.24.2 definition of done — the web user surface.
