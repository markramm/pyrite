---
id: web-user-vocabulary-and-trust-copy-pass
type: backlog_item
title: "Web: user-vocabulary copy pass + trust details (raw enum tokens, server file paths shown to readers, contradictory counts)"
kind: improvement
status: proposed
priority: medium
effort: M
created: "2026-07-03"
tags: [web, copy, ux, trust, ux-audit-2026-07]
links:
- target: web-sidebar-ia-regroup
  relation: related
  kb: pyrite
---

## Problem

The 2026-07-03 live walkthrough found system vocabulary saturating
user-facing surfaces, plus small contradictions that erode trust:

**Vocabulary (system tokens where users need plain words):**
- Raw enum type names in filters and legends: `backlog_item`,
  `cascade_event`, `adr`, `design_doc` — underscores and all.
- Relation names leak underscores: "Links to: OODA Loop (corrects),
  Chet Richards (written_by)".
- "Min importance" filters and bare unlabeled importance numbers on
  Timeline rows and entry cards.
- "Keyword / Semantic / Hybrid" search modes with no explanation;
  bare "Save" link on search.
- Collections empty state directs in developer vocabulary
  ("Add a `__collection.yaml` file… or create a virtual collection").
- Entries status filter merges two state machines into one pile:
  "draft confirmed reported disputed unverified rumor retracted
  active resolved closed".
- Counter-example to copy FROM: the AI menu ("Summarize / Suggest
  Tags / Find Links / Ask AI about this") — plain user verbs.

**Trust details:**
- The entry metadata panel prints the SERVER filesystem path
  ("File: /data/boyd/sources/…md") to every reader — noise for
  users and an information leak on a hosted multi-user instance
  (flag for the pilot's hosting-security posture).
- Contradictory counts on adjacent screens: KB switcher "guide (27)"
  vs Orient "22 entries"; Overview "Tags 3004" vs Tags page "100
  tags across all KBs".
- Entry-list snippets truncate mid-token into raw wikilink syntax:
  "…their intellectual context than [[cor".

## Fix

1. Humanize type/relation display names (one display-name map fed
   by plugin type metadata — `title()` + underscore→space as
   fallback), keep raw tokens in tooltips/filters for power users.
2. Hide the file path behind a "details" affordance; on hosted
   instances show a KB-relative path at most.
3. Reconcile the count sources (or label them: "27 files / 22
   indexed entries" if that's the real distinction — which would
   also surface index drift honestly).
4. Snippet truncation strips unclosed wikilink/markdown syntax.
5. One pass over filter/mode labels with the user-vocabulary test;
   short helper text on search modes.

## Acceptance criteria

- No user-facing surface shows underscore enum tokens outside
  developer tooltips.
- No absolute server paths rendered for non-admin users.
- Switcher and Orient agree (or explain their difference) for the
  same KB.
