---
id: normalize-cascade-timeline-files
type: backlog_item
title: "Normalize cascade-timeline repo layout and frontmatter"
kind: chore
status: proposed
priority: medium
effort: S
tags: [data-quality, cascade]
---

Clean up the cascade-kb/cascade-timeline repo so it's self-consistent and
easy to work with.

1. Remove all 15 `.md.bak` files (leftover from past edits).
2. Reconcile `cascade-timeline/events/` subdirectory (25 entries) — either
   merge into root with date-prefix filenames or document the split in
   `kb.yaml`.
3. Canonicalize frontmatter field order: `type → id → date → title →
   importance → status → tags → actors → sources → body`.
4. Check in `scripts/normalize.py` (the one used today) so drift can be
   caught repeatably.

Applies to `/Users/markr/cascade-kb/cascade-timeline/` only. The retired
internal copy at `tcp-kb-internal/cascade-timeline/` should eventually be
archived — see the wider epic.

Blocks: nothing. Unblocks: stable baseline for consolidate-event-type work.
