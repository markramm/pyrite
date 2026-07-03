---
id: links-asymmetric-intra-kb-mode
type: backlog_item
title: "Add intra-KB mode to `links asymmetric` (single `-k`, non-reciprocal wikilinks within one KB)"
kind: improvement
status: proposed
priority: medium
effort: S
created: "2026-07-02"
tags: [links, audit, cli, field-reported]
---

## Problem

`links asymmetric --kb-a X --kb-b Y` only finds one-directional links
*between two different KBs*. The most common cross-linking debt is
intra-KB hub-and-spoke: a high-importance synthesis theme links its
source entries, but the sources never link back up to the synthesis.
Observed repeatedly in cascade-research; currently requires a custom
pass or per-entry `links suggest`.

Found 2026-06-15 in field use; previously tracked only in
`KNOWN-ISSUES.md`. Promoted to the backlog 2026-07-02.

## Fix

Support `links asymmetric -k <kb>` (single KB): report A→B wikilinks
where B→A is absent within that KB. Optional `--min-importance` filter
so the report starts from the entries that matter.

## Acceptance criteria

- `pyrite links asymmetric -k cascade-research` returns intra-KB
  one-directional links without a second `--kb-b`.
- JSON output shape matches the cross-KB mode.
- `KNOWN-ISSUES.md` entry replaced with a pointer here.
