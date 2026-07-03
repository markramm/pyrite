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

## Decision (2026-07-03, Mark)

**IBM Plex Serif 600 (display) + IBM Plex Sans 400/600 (body).**
Chosen from a four-candidate comparison rendered on the real chrome
(DM Serif Display+DM Sans / DM Sans solo / Fraunces+DM Sans / IBM
Plex pair). Rationale: the Plex family's cohesion reads
records-and-systems, which fits pyrite's institutional target users;
personality lives in the accent layer (gold, Py monogram,
empty-state copy, micro-interactions), which can be dialed up later
without re-fonting — "add a little flair elsewhere to keep the
default from being too institutional."

Notes: this supersedes the 0.8 milestone's "DM Serif Display" —
update that record. Keep JetBrains Mono as the code face (it's
better for code than Plex Mono); revisit only if family purism
starts to matter. DM Sans and the Inter declaration both go.

**Implementation references (2026-07-03):** the full executable spec
is [[web-design-system-spec]] (kb/designs/) — includes the decided
entry-type categorical palette (dark + light variants) for the
constants.ts single-source item, and four canonized patterns (type
badge, epistemic callout, verification status line, wikilink roles).
The visual reference of record is the approved Claude Design file
`Pyrite Design System.dc.html` (project
dcf16160-dc3f-419f-9861-d55f3161d4c4 on claude.ai/design); the
spec's §4b lists the amendments where the canvas demo must NOT be
copied (flat sidebar, load-triggered glint, CDN fonts, off-spec
radii). Implement from the spec; use the canvas for visual QA.

## Fix

1. Load IBM Plex Serif 600 + IBM Plex Sans 400/600 (latin subsets,
   ~53 KB total woff2); remove DM Sans and the phantom Inter
   declaration from `app.css:8-10` and `app.html:10`; update the
   0.8 milestone note in the roadmap/CHANGELOG to record the
   supersession.
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
- Declared fonts are loaded fonts (Plex Serif/Sans + JetBrains
  Mono, nothing else); page titles share one treatment in Plex
  Serif 600.
- One type-color source of truth.
