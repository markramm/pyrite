---
id: web-brand-tokens-implementation
type: backlog_item
title: "Web: implement the brand as tokens — declared fonts aren't loaded, gold is garnish while blue-600 does the work"
kind: improvement
status: proposed
priority: medium
effort: M
created: "2026-07-03"
tags: [web, design-system, branding, ux-audit-2026-07]
---

## Problem

The 0.8 milestone brand ("gold accent, DM Serif Display, Py
monogram") is not what the code ships:

- `app.css:10` declares `--font-display: 'DM Sans'` (not DM Serif
  Display); `app.html:10` loads only DM Sans + JetBrains Mono.
- `--font-sans: 'Inter'` is declared (`app.css:8`) but Inter is
  never loaded — body text silently falls back to system-ui.
- `--font-display` is used in exactly 2 places (sidebar wordmark,
  `h1.page-title` which only /overview uses); every other page
  title is plain `font-bold`.
- Gold appears in ~5 decorative spots while **every primary action
  is default Tailwind blue-600** (entry page :379, overview :61,
  orient :77, CommentsPanel :69, EmptyState :25, wikilinks
  `app.css:144`). Graph hover uses `#facc15` (Tailwind yellow-400),
  not the brand gold `#D4A843`.
- The white-label system pushes `--brand-primary`
  (`+layout.svelte:117-123`) but the hardcoded blue-600s ignore it —
  white-labeling changes the wordmark and little else.
- `constants.ts:4-64` maintains type colors twice in parallel (hex
  map + Tailwind-class map), already drifted (`concept`/`project`
  exist only in the class map).

The design system is one 9-line `@theme` block — the debt is
shallow, so this is a mechanical consolidation, not a redesign.

## Fix

1. DECIDE the brand (operator call): DM Serif Display per the
   milestone, or ratify DM Sans and update the milestone record.
   Load whatever is decided; delete or load Inter.
2. Route all primary actions and interactive accents through
   `--brand-primary` (making white-labeling real); reserve gold per
   the brand decision.
3. Apply the display face to all page titles (one `.page-title`
   class used consistently).
4. Generate the type-color Tailwind classes from the hex map (one
   source of truth) in `constants.ts`.
5. Add semantic tokens for the handful of hardcoded grays/reds in
   entry-page transclusion code (`entries/[id]/+page.svelte:125,153`)
   and GraphView while in there.

## Acceptance criteria

- Zero blue-600 primary buttons; changing `--brand-primary` visibly
  rebrands the app.
- Declared fonts are loaded fonts; page titles share one treatment.
- One type-color source of truth.
