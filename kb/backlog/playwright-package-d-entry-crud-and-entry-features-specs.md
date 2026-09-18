---
id: playwright-package-d-entry-crud-and-entry-features-specs
title: 'Playwright package D: entry-crud and entry-features specs against the seeded world'
type: backlog_item
tags:
- testing
- e2e
- web
- playwright
kind: task
status: in_progress
priority: high
effort: M
assignee: agent:pyrite-worker
---

## Problem

`web/e2e/entry-crud.spec.ts` (186 lines) and `web/e2e/entry-features.spec.ts`
(184 lines) are the largest pair in the fan-out and the only two that **write**.
They were written against an undefined world, so their assertions are
either-way (`locator(A).or(locator(B))`) and their created entries collide with
each other on re-runs.

Package A defined the world and gave writing specs the tools they need:
`uniqueTitle()` and `idForTitle()` in `web/e2e/fixtures.ts`. A spec that creates
must use them — never a fixed title, which collides with itself on a second run
inside one seeded world, and never a title another spec asserts on.

## Acceptance

- [ ] Both specs assert on seeded data from `fixtures.ts`, never on
      "a list or an empty state".
- [ ] Every entry these specs create uses `uniqueTitle()`; none writes a title
      another spec reads.
- [ ] Zero `text=` locators; no `.first()` used to dodge a strict-mode
      violation.
- [ ] Both pass 5x in a row against A's world.
- [ ] A real product bug found by a now-real assertion is reported and marked
      `test.fixme` with the bug named, never papered over with a weaker
      assertion.

Part of
[[playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap]],
Package D. 0.24.2 definition of done — the web user surface.
