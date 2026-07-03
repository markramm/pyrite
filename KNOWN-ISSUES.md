# Known Issues

Bugs found in field use, pending fix.

## `pyrite links asymmetric` is cross-KB only — no intra-KB one-directional-link detection

**Found:** 2026-06-15.

**Symptom (by design, but a gap):** `links asymmetric --kb-a X --kb-b Y` finds one-directional links *between two different KBs*. There is no mode to find one-directional (non-reciprocal) wikilinks *within a single KB*.

**Why it matters:** the most common cross-linking debt is intra-KB hub-and-spoke: a high-importance synthesis theme links its source entries, but the sources don't link back up to the synthesis. `links asymmetric` cannot surface these because both ends live in the same KB (e.g. cascade-research). An audit of cascade-research's internal reciprocity currently requires a custom pass.

**Requested:** an intra-KB mode, e.g. `links asymmetric -k cascade-research` (single `-k`, report A→B links where B→A is absent within that KB).

**Impact:** the "sources don't link back to the synthesis hub" debt (observed repeatedly in cascade-research) can't be found with built-in tooling; needs `links suggest` per-entry or a custom script.
