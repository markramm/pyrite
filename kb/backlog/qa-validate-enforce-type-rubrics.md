---
id: qa-validate-enforce-type-rubrics
type: backlog_item
title: "qa validate must enforce kb.yaml type-level rubric checkers; reconcile rubric vs corpus"
kind: improvement
status: proposed
priority: medium
effort: M
created: "2026-07-02"
tags: [qa, kb, rubric, dogfooding]
---

## Problem

The dogfooding loop has a hole: `pyrite qa validate pyrite` returns
749 findings but does NOT run the type-level rubric checkers declared
in kb.yaml (`body_has_section`, `has_field` params), so the KB fails
its own quality bar invisibly (2026-07-02 audit):

- 0 of 28 ADRs have the `## Alternatives` section the ADR rubric
  requires — the corpus uniformly uses Nygard-style
  Context/Decision/Consequences and the rubric was never reconciled.
- 15 of 65 component docs missing the required `dependencies` field
  (incl. index-manager, git-service, template-service).
- `index-manager.md` is a 1-sentence stub for the module at the center
  of the derived-state bug class; backend docs don't mention
  `base_backend.py`/`overlay_backend.py`/`capabilities.py`.
- 23 schema `kind`-enum errors, 16 broken wikilinks in architecture
  docs (ADR wikilinks use file-number form `0014-...` while entry IDs
  are `adr-NNNN` — breaks graph navigation between ADRs 0014/0017).
- Related discoverability tax: search ranks long done-backlog bodies
  above component docs/ADRs on dev queries; the fix is already filed
  ([[search-relevance-boost-by-entry-type]]) and unimplemented.

## Fix

1. Wire the declared type-level rubric checkers (has_field,
   body_has_section, status_present, priority_present,
   descriptive_title) into `qa validate` so kb.yaml rubrics are
   enforced, not decorative.
2. Reconcile the ADR rubric with reality: either adopt
   Context/Decision/Consequences as the required sections (recommended
   — the corpus is consistent and Context argues alternatives inline)
   or retrofit Alternatives sections. Decide once, in kb.yaml.
3. Fix the 23 kind-enum violations and 16 broken wikilinks; normalize
   ADR wikilink form to entry IDs (`adr-NNNN`).
4. Backfill `dependencies` on the 15 non-compliant component docs;
   write a real body for index-manager.md (staleness/health machinery)
   and update backend docs for the base/overlay/capabilities modules.
5. While in there: update the stale
   [[file-missing-adrs-for-session-arc-decisions]] ticket — it
   proposes ADR numbers 0027/0028 that have since been consumed;
   executing it as written creates collisions.

## Acceptance criteria

- `qa validate pyrite` reports rubric-checker findings (and the count
  drops to zero after the backfill).
- No broken wikilinks among ADRs/components; kind-enum errors zero.
- A CI-mode `pyrite ci` run fails on new rubric violations, so drift
  can't re-accumulate invisibly.
