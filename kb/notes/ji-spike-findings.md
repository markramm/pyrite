---
id: ji-spike-findings
title: "JI spike findings: what the FollowTheMoney exploration taught the architecture"
type: note
status: active
author: markr
date: "2026-07-04"
tags: [journalism-investigation, spike, ftm, extensibility, findings, retrospective]
links:
- target: adr-0022-typed-relationship-entries-edge-entities
  relation: related
  kb: pyrite
- target: plugin-type-resolution-scoping
  relation: related
  kb: pyrite
- target: ji-absorb-cascade-types
  relation: supersedes
  kb: pyrite
---

# JI Spike Findings

**Reframe (2026-07-04, Mark):** the journalism-investigation
extension "may have started as a product idea, but it was really a
**spike**" — an exploration of the problems FollowTheMoney would
present, the ways to solve them, and how that fits pyrite's
extensibility framework. The product framing explains why the
artifacts are dressed as product (five `done` epics, a
high-priority absorb ticket, a UI epic); the spike reading is what
the evidence supports. Built 2026-03-11→14 (~5.7K LOC, 364 tests);
exploration complete; this note is the close-out that was missing.
Judged as a spike, it succeeded.

## What the spike yielded

1. **It forced edge entities into core.** ADR-0022 (typed
   relationships as first-class entries) was accepted the week the
   JI design landed and was informed by it. The domain exploration
   ended; the extracted architecture is production infrastructure.
2. **It stress-tested the extensibility framework at full width** —
   11 entry types, 17 relationship types, 23 MCP tools, hooks,
   validators, KB presets, a CLI sub-app — and the framework held.
   The 2026-07-03 code audit independently rated JI the
   reference-quality extension (clean plugin shell over pure query
   modules). It remains the extension framework's best worked
   example (see extensions/journalism-investigation/README.md).
3. **It exposed the framework's real gaps**, now ticketed:
   global type-remapping with no KB-type scoping
   ([[plugin-type-resolution-scoping]] — the person→actor blast
   radius), last-writer-wins type conflicts, extension vocabulary
   leaking into core `_UPDATE_FIELDS`, the missing plugin capability
   matrix. These were undiscoverable without an extension this
   ambitious.
4. **It answered the FtM question:** FollowTheMoney's model CAN be
   expressed in pyrite — entities as entries, relationships as edge
   entities, interop via ftm.py import/export, ownership/money-flow
   analytics over the edge graph. The mapping works.
5. **The negative finding is also a finding:** schema-first
   claim/evidence discipline lost to prose-conventions-plus-
   conductor-QC in 3.5 months of the heaviest possible dogfooding
   (5,500-event timeline, 365+ actor profiles built alongside the
   idle machinery; zero claim/evidence/transaction entries in
   production). Investigative practice, at least this operation's,
   wants verification discipline in workflow gates and source-tier
   conventions, not in typed claim objects. Any future FtM work
   should treat the schema as an interop/exchange layer, not as the
   working discipline.

## What is alive vs. archived

- **Alive (load-bearing):** `InvestigationEventEntry` (base of
  cascade's `timeline_event` — 5,505 production entries),
  `query_network`, the edge-type declarations, KB presets.
- **Archived-in-place (exploratory domain machinery, unused in
  production):** claims/evidence chain, financial layer
  (transaction/ownership/membership/funding + money-flow +
  ownership-chain analytics), source-reliability system, FtM/Aleph
  import-export, dedup, pack export, the `pyrite investigation` CLI.
  Kept compiling and tested; not maintained as product surface. Git
  is the archive if pruning ever wins.
- **Scheduled fixes (0.25, unchanged):** the `_base_kwargs`
  divergence (drops `_schema_version`; raw `int()` importance) via
  [[shared-frontmatter-split-utility]] — the one JI defect touching
  production data.

## FtM is a future roadmap idea, not a current workstream

Recorded on the roadmap (Future → Ecosystem): **FtM/Aleph interop**
as a gated revival. The OCCRP ecosystem is exactly the
peer-journalist world the shared-instance pilot serves — the revival
trigger is *a pilot peer asking for claims/evidence features or
Aleph import by name*. The spike means revival starts from a working
mapping and a tested import/export layer, not from zero. Until that
trigger: no feature work, no UI epics
(ji-ui-* tickets stay demoted/frozen per 2026-07-02).

## Decisions this note records

- [[ji-absorb-cascade-types]] (May 2026, proposed-high, rank 100) is
  **retired** — it was written from the product reading of JI
  (make JI the canonical schema home). The spike reading inverts it:
  cascade owns the production types; JI keeps only the base class
  until its three fields migrate to cascade or core EventEntry
  (naming/inheritance decision open, low urgency, 0.26+).
- Extraction-to-separate-repo (option D) is impractical until that
  inheritance edge moves; revisit alongside the social-plugin
  extraction if ever.
