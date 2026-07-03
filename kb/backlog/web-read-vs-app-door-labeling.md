---
id: web-read-vs-app-door-labeling
type: backlog_item
title: "Web: 'Read' vs 'Explore in app' — two products behind unexplained doors, no cross-navigation"
kind: improvement
status: proposed
priority: medium
effort: S
created: "2026-07-03"
tags: [web, ia, landing, ux-audit-2026-07]
links:
- target: epic-pyrite-publication-strategy
  relation: related
  kb: pyrite
---

## Problem

Landing-page KB cards offer two unexplained doors: "Read"
(→ `/site/<kb>`, a minimal static-chrome reader with its own
HOME/SEARCH nav) and "Explore in app" (→ `/orient?kb=`). Nothing
says how they differ; a user who enters via "Read" lands in what
looks like a second product with no sidebar and no way to discover
the app exists (and vice versa — no "open in reader" from the app).

The split itself is intentional architecture
([[epic-pyrite-publication-strategy]]: "consumption is static,
investigation is live") — the problem is purely that the UX doesn't
communicate it or bridge it.

## Fix

1. Label the doors by what the user gets: e.g. "Read (clean reading
   view)" vs "Open workspace (search, graph, editing)" — exact copy
   TBD, user-vocabulary test applies.
2. Cross-navigation: the site chrome gets an "Open in workspace"
   link (auth-gated), entry pages get "View as published" where a
   site exists.
3. Landing sidebar contradiction: the app sidebar is already
   rendered on `/` showing "guide (27)" while the page content is
   global — either scope the landing (no sidebar) or make the
   sidebar reflect the page. Also hide zero-entry demo cruft KBs
   (`pyrite2 (0)`, `testme (0)`) from the public landing.

## Acceptance criteria

- A user can say, before clicking, what each door is for — and can
  cross from either surface to the other in one click.
