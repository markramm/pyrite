---
body: "## Problem\n\n`web/e2e/collections.spec.ts` (50 lines) and `web/e2e/daily.spec.ts` (176 lines)\nare the two specs whose determinism depends most directly on what Package A\nseeded, and the two most likely to have been passing by accident.\n\n- Collections: the world has exactly one, `SEEDED_COLLECTION` — a query\n  collection over `type:person`, so it is never empty and its membership is the\n  three seeded people.\n- Daily: A pre-created every date the daily specs navigate to\n  (`SEEDED_DAILY_DATES` — a fixed date plus offsets -3..+2 from today) precisely\n  because, with auth disabled, `GET /daily/{date}` **creates** a note for a date\n  that has none. Any date these specs reach outside that set turns a read into a\n  write and leaves the world changed.\n\n## Acceptance\n\n- [ ] Both specs assert on seeded data from `fixtures.ts`, never on\n      \"a list or an empty state\".\n- [ ] `daily.spec.ts` navigates only to dates in `SEEDED_DAILY_DATES`; if a\n      prev/next click would leave that set, either the spec stops at the edge or\n      the range is extended in `fixtures.ts` — and extending it is A's file, so\n      it is reported, not edited.\n- [ ] Zero `text=` locators; no `.first()` used to dodge a strict-mode\n      violation.\n- [ ] Both pass 5x in a row against A's world.\n- [ ] A real product bug found by a now-real assertion is reported and marked\n      `test.fixme` with the bug named, never papered over.\n\nPart of\n[[playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap]],\nPackage E. 0.24.2 definition of done — the web user surface."
file_path: /Users/markr/pyrite-wt/feature-playwright-package-e/kb/backlog/playwright-package-e-collections-and-daily-specs.md
id: playwright-package-e-collections-and-daily-specs
title: 'Playwright package E: collections and daily specs against the seeded world'
type: backlog_item
tags:
- testing
- e2e
- web
- playwright
importance: 5
kind: task
status: done
priority: high
assignee: agent:pyrite-worker
effort: M
rank: 0
---

## Problem

`web/e2e/collections.spec.ts` (50 lines) and `web/e2e/daily.spec.ts` (176 lines)
are the two specs whose determinism depends most directly on what Package A
seeded, and the two most likely to have been passing by accident.

- Collections: the world has exactly one, `SEEDED_COLLECTION` — a query
  collection over `type:person`, so it is never empty and its membership is the
  three seeded people.
- Daily: A pre-created every date the daily specs navigate to
  (`SEEDED_DAILY_DATES` — a fixed date plus offsets -3..+2 from today) precisely
  because, with auth disabled, `GET /daily/{date}` **creates** a note for a date
  that has none. Any date these specs reach outside that set turns a read into a
  write and leaves the world changed.

## Acceptance

- [x] Both specs assert on seeded data from `fixtures.ts`, never on
      "a list or an empty state".
- [x] `daily.spec.ts` navigates only to dates in `SEEDED_DAILY_DATES`; if a
      prev/next click would leave that set, either the spec stops at the edge or
      the range is extended in `fixtures.ts` — and extending it is A's file, so
      it is reported, not edited.
- [x] Zero `text=` locators; no `.first()` used to dodge a strict-mode
      violation.
- [x] Both pass 5x in a row against A's world.
- [x] A real product bug found by a now-real assertion is reported and marked
      `test.fixme` with the bug named, never papered over.

Part of
[[playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap]],
Package E. 0.24.2 definition of done — the web user surface.
