---
id: web-design-system-spec
type: design_doc
title: "Pyrite Web Design System Spec — type, color, and component rules (handoff for implementation)"
status: accepted
author: markr
date: "2026-07-03"
reviewers: []
tags: [web, design-system, branding, typography, ux-audit-2026-07]
---

# Pyrite Web Design System Spec

**Purpose:** a self-contained spec an implementing session can execute
without re-deriving decisions. Covers typography, color tokens, and
component treatment rules. Decided 2026-07-03 by Mark from a
four-candidate comparison rendered on the real chrome.

**Implements/unblocks:** [[web-brand-tokens-implementation]] (primary),
[[web-light-mode-chrome-repair]]. **Coordinates with (do not solve
here):** [[web-sidebar-ia-regroup]], [[web-kb-context-single-authority]],
[[web-graph-default-scope-and-guards]],
[[web-user-vocabulary-and-trust-copy-pass]] — this spec is tokens +
treatment, not IA or copy.

---

## 1. Design stance

Pyrite is an evidence archive for investigative journalists,
institutional research teams, and their AI agents. The default
identity is **credible-institutional**: the type system reads like
well-kept records. Personality is deliberately budgeted to the
**accent layer** (gold, the Py monogram, empty-state voice,
micro-interactions), which can be dialed up or down — and replaced
entirely by white-label deployments — without re-fonting the product.

One sentence to test every choice against: *would an institutional
research team trust this screen on first sight, and would a solo
journalist still feel it has a pulse?*

## 2. Typography

**Family decision (2026-07-03, supersedes the 0.8 milestone's "DM
Serif Display"):**

| Role | Face | Weights | Notes |
|---|---|---|---|
| Display | **IBM Plex Serif** | 600 | Titles only — used with restraint |
| Body / UI | **IBM Plex Sans** | 400, 500, 600 | Everything else |
| Code / data | **JetBrains Mono** | 400 | Unchanged; deliberate non-Plex (better code face) |

Remove: DM Sans (all weights), the phantom `Inter` declaration
(`app.css:8` — declared, never loaded). Load latin subsets as woff2
(~70 KB total for the set above); self-host rather than Google CDN if
the hosted-instance privacy posture prefers it (see
[[hosting-security-requirements]] REQ-1 spirit).

**Where Plex Serif 600 appears — exhaustive list:**
- The wordmark ("pyrite") in the sidebar and landing.
- Page titles (one `.page-title` class; every route uses it — today
  only /overview does).
- Entry titles (the h1 on `/entries/[id]`).
- Landing hero headline.
- Section headings on the static `/site/<kb>` reader.

**Where it must NOT appear:** buttons, nav items, chips, form labels,
table headers, tooltips, toasts, body prose. If a surface is operated
rather than read, it's Plex Sans.

**Scale** (rem at 16px base; line-height; tracking):

| Token | Size / LH | Face·Weight | Use |
|---|---|---|---|
| `display-xl` | 34px / 1.15 | Serif 600 | Landing hero |
| `display` | 28px / 1.2 | Serif 600 | Page titles |
| `title` | 22px / 1.25 | Serif 600 | Entry titles, modal titles |
| `heading` | 16px / 1.4 | Sans 600 | Card/section headings |
| `body` | 15px / 1.6 | Sans 400 | Prose, max-width 65ch |
| `ui` | 13.5px / 1.45 | Sans 400–500 | Nav, controls, chips |
| `caption` | 12px / 1.4 | Sans 400 | Meta, timestamps |
| `label` | 11px / 1.3 | Sans 600, +0.08em tracking, uppercase | Eyebrows, group headers |
| `code` | 13px / 1.55 | Mono 400 | IDs, paths, code |

Numbers in data contexts (stats, counts, tables): Plex Sans 600 with
`font-variant-numeric: tabular-nums`. Serif numerals only in landing
editorial moments.

## 3. Color

**Token architecture:** one `@theme` block in `app.css` remains the
single source; components consume semantic tokens, never raw
palette values. Semantic status colors are separate from the accent
and don't count as accent usage.

### Palette (dark = default theme)

| Token | Dark | Light | Use |
|---|---|---|---|
| `--ground` | `#0B0B0D` | `#FAFAF8` | Page background (warm-biased near-black / warm off-white — chosen neutrals, not zinc defaults) |
| `--surface` | `#17171A` | `#FFFFFF` | Cards, panels |
| `--surface-2` | `#1E1E22` | `#F2F1EE` | Nested/hover surfaces |
| `--line` | `#2A2A30` | `#E3E1DC` | Borders, dividers |
| `--ink` | `#E6E4DF` | `#1F1E1B` | Primary text |
| `--ink-muted` | `#9D9DA6` | `#6E6C66` | Secondary text |
| `--ink-faint` | `#6B6B74` | `#98958D` | Tertiary/meta text |

### Accent (the brand layer)

| Token | Dark | Light | Use |
|---|---|---|---|
| `--brand-primary` | `#D4A843` | `#8A6F2E` | Interactive accent: links, active nav, focus rings, primary-button borders/text-on-dark |
| `--brand-fill` | `#D4A843` | `#D4A843` | Solid fills (monogram, primary buttons) — always with `--brand-on-fill` text |
| `--brand-on-fill` | `#141414` | `#141414` | Text on gold fills |

Rules:
- **Kill blue-600 entirely.** Every primary action, wikilink, tag
  pill, and active state routes through `--brand-primary` /
  `--brand-fill`. This is also what makes the existing white-label
  `--brand-primary` override actually work.
- Gold `#D4A843` on white fails text contrast — that's why light
  mode gets the darker `#8A6F2E` for text/link/icon usage while
  solid fills keep `#D4A843` (with dark text, 8.5:1). Never use
  raw gold as light-mode text.
- Primary button: gold fill + `--brand-on-fill` text (dark theme);
  same in light. Secondary button: transparent, `--line` border,
  `--ink` text. Destructive: semantic red, never gold.

### Semantic status (separate axis from accent)

| Token | Dark | Light |
|---|---|---|
| `--ok` | `#5FA97A` | `#3E7A55` |
| `--warn` | `#C9924B` | `#96692F` |
| `--critical` | `#C96257` | `#A5443A` |

(Warn is deliberately shifted toward amber-brown so it never reads
as the brand gold.)

### Entry-type colors (categorical axis — decided)

One source of truth: the hex map in `constants.ts`; the Tailwind
class map is **generated** from it (today they're parallel and
already drifted — `concept`/`project` exist in one only).

The core-type palette (from the approved Claude Design reference,
2026-07-03 — distinct hues at matched lightness, darkened variants
for light-mode contrast):

| Type | Dark | Light |
|---|---|---|
| person | `#6E9BD6` | `#3F6FB0` |
| event | `#6DBE8E` | `#3E8A5E` |
| note | `#B58BD6` | `#7E52A8` |
| concept | `#5FC0C0` | `#2E8E8E` |
| project | `#D69A5F` | `#A86A2E` |
| source | `#D67F9B` | `#A84E6C` |

Extension/plugin types extend this palette with the same method
(distinct hue, matched lightness, darkened light variant). Blue is
legal HERE because this is the data axis, not the interactive axis —
the no-blue rule in §3 applies to actions and links only. Verify the
palette on the graph legend specifically (the current greys decode
nothing there).

## 4. Component treatment rules

- **Radius:** 6px controls, 10px cards/panels, 999px chips. No other
  values.
- **Spacing:** 4px base scale (4/8/12/16/24/32/48). Sibling groups
  use flex/grid `gap`, not per-element margins.
- **Focus:** every interactive element gets a visible 2px
  `--brand-primary` focus ring (`:focus-visible`), both themes.
- **Empty states:** always the shared `EmptyState` component (fix its
  dark-hardcoded text while migrating), and always with one
  directing action — "an empty screen is an invitation to act."
  Model copy: the empty-KB entries state ("Create your first entry
  to start building your knowledge base").
- **Graph canvas:** theme-derived colors (ground/line/label from
  tokens), never hardcoded `#09090b` (`GraphView.svelte:271-275`);
  node hover ring uses `--brand-primary`, not Tailwind yellow-400.
- **Loading:** skeletons must be bounded — any fetch that can fail
  resolves to content, an error state, or an empty state; permanent
  skeletons are a defect (see [[web-search-results-never-render]]).
- **Both themes are first-class.** Every new/touched component ships
  with light and dark verified; the known dark-hardcoded list is in
  [[web-light-mode-chrome-repair]]. Respect
  `prefers-reduced-motion` on all transitions.

## 4b. Patterns canonized from the Claude Design reference (2026-07-03)

The visual reference of record is the Claude Design project **"Web
design system spec"**, file `Pyrite Design System.dc.html`
(claude.ai/design project `dcf16160-dc3f-419f-9861-d55f3161d4c4`) —
reviewed against this spec and approved. Four patterns from it are
now spec, with roles:

1. **Type badge** — pill with 16% tint of the type color as
   background, a solid type-color dot, and type-color text (e.g.
   `background: color-mix(in srgb, var(--t-source) 16%, transparent)`).
   This is also the display answer for raw enum tokens: badges show
   humanized names ("source"), never `backlog_item`-style tokens.
2. **Epistemic callout** — a block with a 2px `--warn` left border
   and muted text for unconfirmed/pending-corroboration content
   ("Unconfirmed: … corroboration pending"). Evidentiary status as
   visual grammar; use for anything below the piece's verification
   bar. A `--ok` variant may mark corroborated-update callouts.
3. **Verification status line** — entry byline row carries a small
   semantic dot + label ("● verified source") on the semantic axis,
   never gold.
4. **Wikilink roles** — in prose: gold text with a 40%-alpha gold
   bottom-border underline. In LISTS (backlinks panel, "Links to"
   rows): the gold-bordered chip form. Never both in the same
   context; never the chip form inside prose.

Amendments to the reference (do NOT copy these from the canvas):
the demo's flat sidebar predates [[web-sidebar-ia-regroup]] — take
sidebar STRUCTURE from that ticket, treatment (gold inset tick +
`--surface-2` active fill) from the reference; the monogram glint
binds to first-load-per-session or hover in product, not every
navigation; fonts are self-hosted in product, not Google CDN; radius
stays on the 6/10 rule (the canvas's 8px swatches and 14px outer
frames are demo chrome).

## 5. The flair budget (deliberate, dial-able, additive)

Personality lives ONLY here, so institutions get a credible default
and the flair can be tuned or white-labeled away:

1. **The Py monogram** — the one wry brand mark (pyrite = fool's
   gold; the name is a joke about what unexamined information is
   worth — mine it anyway). It may carry one micro-interaction
   (e.g. a brief glint on hover/load). Nothing else animates for
   personality.
2. **Gold moments** — search-result `<mark>` highlights, active-nav
   ticks, the entry-importance indicator. Functional locations that
   happen to be branded, not decoration.
3. **Empty-state and success voice** — plain verbs, warm register
   (the AI menu's "Summarize / Suggest Tags / Find Links" is the
   house style). This is where warmth goes; the chrome stays quiet.

If the default ever reads too institutional, dial THIS layer up —
do not add typefaces, gradients, or decoration to the chrome.

## 6. Quality floor (non-negotiable)

Keyboard-visible focus everywhere; WCAG AA contrast for text in both
themes (spot-check `--ink-muted` on `--surface-2` in light);
`prefers-reduced-motion` respected; no horizontal page scroll at
390px; tabular-nums wherever digits align.

## 7. Implementation map

| Change | Where |
|---|---|
| Font loading (Plex Serif 600, Plex Sans 400/500/600, JB Mono 400; remove DM Sans/Inter) | `web/src/app.html:10`, `web/src/app.css:3-11` |
| Token block (this spec's §3 palette, both themes) | `web/src/app.css` `@theme` |
| `.page-title` applied on every route | all `routes/*/+page.svelte` |
| blue-600 → `--brand-primary`/`--brand-fill` sweep | `entries/[id]/+page.svelte:379`, `overview:61`, `orient:77`, `CommentsPanel:69`, `EmptyState:25`, `app.css:144` (wikilinks), tag pills, + grep for `blue-600\|blue-500` |
| Type-color single source (generate class map from hex map) — adopt the §3 categorical palette (dark + light variants) as the new hex map | `web/src/lib/constants.ts:4-64` |
| Graph theme-aware + brand hover | `GraphView.svelte:119,171-180,271-275` |
| EmptyState theme fix + adoption pass | `common/EmptyState.svelte:19` + rolled-own empty states in overview/landing/comments |
| Milestone record correction (DM Serif Display → superseded) | `kb/roadmap.md` 0.8 note |

**Definition of done:** changing `--brand-primary` alone visibly
rebrands the app (white-label test); zero blue-600 anywhere; fonts
loaded = fonts declared; both themes pass the §6 floor; the four-
candidate comparison page's Candidate D look is what ships.

## 8. Out of scope for this spec

Sidebar IA/grouping, KB-context routing, graph default scope, copy
rewrites, and the two pilot-blocking bugs — all separately ticketed
(see header). An implementing session should not "improve" those
here; treatment changes only.
