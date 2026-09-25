---
id: round-trip-fidelity-a-no-op-save-leaves-the-metadata-and-links-blocks-as
title: 'Round-trip fidelity: a no-op save leaves the metadata and links blocks as written (#178, #90)'
type: backlog_item
tags:
- bug
- storage
- round-trip
importance: 5
kind: bug
status: proposed
priority: medium
effort: M
rank: 0
---

Groups two GitHub issues that have no backlog item: **#178** (new metadata keys should join an existing `metadata:` block; one helper owns the decision between nesting and promoting) and **#90** (a no-op load/save round trip restyles the `links:` block on 148 entries). Proposed for 0.27. Neither loses data: both rewrite what the author wrote. So they sit below the data-loss and wrong-result bugs, but every save through the write path is affected.

## Problem

A load → save with no edit should leave a file byte-identical. `tests/test_roundtrip_identity.py` pins what still isn't: `KNOWN_RESIDUAL_IDS = LINKS_BARE_STRING_IDS | GENERIC_METADATA_DUP_IDS | TRAILING_BLANK_LINE_NORMALIZE_IDS` (strict xfail).
- **Links (#90):** bare-string links are expanded to `{target, relation: related}` mappings, and indented nested sequences are re-indented flush-left. `Entry._base_frontmatter` writes `[l.to_dict() for l in self.links]` (`pyrite/models/base.py:~505`) and keeps no memory of the source form.
- **Metadata (#178):** `Entry._base_frontmatter()` writes `self.metadata` as a nested block unconditionally. `GenericEntry` (`pyrite/models/generic.py:~108`) keeps the keys that arrived nested and promotes the rest, so a new key lands beside the block, half in and half out. `TaskEntry.to_frontmatter` (`pyrite/models/task.py:~455`) pops the block unconditionally, so an author-written nested `metadata:` is flattened on a no-op save.

## Groom 2026-09-25

**Acceptance** (merged verbatim from #178 and #90, plus the gate):
- From #178: "One helper on `Entry` decides the on-disk shape of `metadata`." "A file with a `metadata:` block keeps it, and new keys join it." "A file without one gets promoted top-level keys." "`TaskEntry` and `GenericEntry` both use the helper; no subclass pops or re-adds the block on its own." "Round-trip fixtures (`tests/fixtures/roundtrip/`) cover both types: nested-only, promoted-only, and 'add a key to an all-nested file'."
- From #90: a no-op round trip leaves a `links:` block as written. Bare strings stay bare strings, and nesting and indentation are preserved. A link added or edited through the API is still written in the mapping form.
- `LINKS_BARE_STRING_IDS` and `GENERIC_METADATA_DUP_IDS` in `tests/test_roundtrip_identity.py` are empty, and the strict xfail proves they stopped failing. `TRAILING_BLANK_LINE_NORMALIZE_IDS` is out of scope unless it falls out for free.

**Touches:**
- Existing: `pyrite/models/base.py` (`_base_frontmatter`, `_frontmatter_for_file`), `pyrite/models/generic.py`, `pyrite/models/task.py`, `pyrite/schema/provenance.py` (`Link`, if the source form is carried there), `tests/test_roundtrip_identity.py`, `tests/fixtures/roundtrip/` (new fixtures).
- New: `tests/test_metadata_block_shape.py` (or similar).

**Sequence:**
- After #386 (`pyrite/models/factory.py` GenericEntry branch; the next dispatch).
- After #381 (#378) has merged, so the write pipeline's shape is settled.
- Independent of #379 and #380.
- Conflicts with any theme that edits `pyrite/models/base.py`. None is scheduled.

**Model:** Opus. This is the write-path invariant in `base.py` (#46, 7783335, #151 all live there), and "the source form" has to be carried through without making `Entry` a bag of flags. **Size:** M. **Heavy:** yes (full suite; the round-trip gate walks `kb/`). **Cold read:** yes. It changes the bytes every save writes, which is a file-format question.

**Out of scope:**
- #86. `importance` and `rank` on newly created entries are deliberate (commit 7783335, #46). That is a separate decision; see #86.
- Trailing-blank-line normalisation.
- Frontmatter key order.
- The shared frontmatter split utility ([[shared-frontmatter-split-utility]]).
- Changing how the index reads links.

**Related:** [[typed-entries-silently-drop-the-references-frontmatter-field]]. It appears fixed on `dev`: `entry_from_frontmatter` keeps unknown keys through `capture_extra_frontmatter`, and a sandbox check on 368f7fe2 kept `references:` on `event` and `person`. Verify it with that item's own index-level acceptance test and close it. Do not fold it into this theme.
