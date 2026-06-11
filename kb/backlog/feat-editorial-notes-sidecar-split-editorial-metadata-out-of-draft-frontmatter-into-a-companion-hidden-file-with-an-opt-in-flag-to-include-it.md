---
id: feat-editorial-notes-sidecar-split-editorial-metadata-out-of-draft-frontmatter-into-a-companion-hidden-file-with-an-opt-in-flag-to-include-it
title: "feat: editorial-notes sidecar — split editorial metadata out of draft frontmatter into a companion file (opt-in flag to include it)"
type: backlog_item
tags: [feature, conductor-filed, indexing, drafts-kb, schema]
importance: 6
kind: feature
status: proposed
priority: high
effort: M
---

FEATURE (Mark direction 2026-06-11, from the data-colonialism drafting session). PROBLEM: drafts in the drafts KB carry heavy editorial metadata in frontmatter — editorial_notes (nested mappings + multi-line block scalars), triage_log, fact-check verdicts, reviser logs. This (1) clogs the draft so search returns editorial cruft instead of the piece, (2) bloats the published-surface artifact, and (3) is the PRIMARY SOURCE of malformed-YAML index-sync failures (unquoted colons/em-dashes in verdict strings, bad block-scalar indent, duplicate keys) — ~27 drafts were unindexed because of it as of 2026-06-11.

PROPOSAL: separate editorial metadata from the draft into a COMPANION SIDECAR FILE per draft (e.g. a hidden  or a parallel sidecar the indexer ignores by default). The draft itself keeps only real content + minimal frontmatter (id/title/type/status/tags). The editorial apparatus is preserved (not deleted) but lives outside the searched/published surface.

PYRITE-SIDE WORK: (a) define the sidecar convention + where it lives relative to the entry; (b) index the draft WITHOUT the sidecar by default (so search/list/get surface the clean piece); (c) add an OPT-IN FLAG (e.g.  / ) to get/search/sync that merges the sidecar metadata back in WHEN WANTED (editorial workflows, the draft-conductor). (d) optionally a migration helper that extracts existing editorial_notes/triage_log from frontmatter into sidecars.

WHY THIS IS THE RIGHT FIX (vs the frontmatter-repair currently underway): repair fixes the symptom (malformed YAML) one file at a time; the sidecar fixes the root cause (editorial metadata never belonged in the indexed/published surface). Same 'git/FS is truth, pyrite is the index' principle applied WITHIN the document: keep the editorial apparatus, just not in the thing that gets searched and published. Owner: pyrite repo. Relates to the drafts-KB ScannerError cluster + the from_markdown parser-robustness bug already filed.
