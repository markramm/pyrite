---
id: typed-entries-silently-drop-the-references-frontmatter-field
title: 'Typed entries silently drop the references: frontmatter field'
type: backlog_item
tags:
- bug
- storage
- recall
importance: 5
status: proposed
priority: medium
effort: M
rank: 0
---

## Problem

`references:` in an entry's YAML frontmatter (cross-KB structured links, format `["kb_name:entry_id", "entry_id"]`) survives the parse round-trip for GenericEntry (kb.yaml custom types) but is silently dropped for every core typed entry — EventEntry, PersonEntry, OrganizationEntry, etc.

Root cause: GenericEntry.from_frontmatter collects unknown top-level frontmatter keys into self.metadata (generic.py:64-68), so references ends up in entry.metadata and index.py's extraction picks it up. Core typed entries' from_frontmatter only reads specific known fields (e.g. EventEntry.from_frontmatter reads date/location/actors/notes/status — nothing else), so a references: key is dropped before the Entry object even exists. to_frontmatter() doesn't re-emit it either (it only emits the same specific known fields), so index.py's to_frontmatter()-based fallback (storage/index.py:295-320) can never recover it for typed entries — there's nothing to recover.

Reproducible:

```python
from pyrite.models.core_types import EventEntry
meta = {"id": "ev1", "title": "Test", "type": "event", "date": "2025-01-01", "references": ["other-kb:target-1"]}
entry = EventEntry.from_frontmatter(meta, "body")
entry.metadata  # {} -- references is gone
entry.to_frontmatter().get("references")  # None
```

Found while fixing fail-open-exception-sweep site #4 (index.py:306-311's swallowed to_frontmatter() exception) — that fix makes the *failure path* visible, but the *structural* gap (references never reaching the entry at all for typed entries) is a separate, larger bug.

## Fix

references: should round-trip for every core Entry subclass, not just GenericEntry. Candidate approaches:

1. Add references handling to Entry._base_kwargs/_base_frontmatter (base.py) so every from_frontmatter/to_frontmatter override gets it via the shared helper, matching how sources/links/provenance already work there.
2. Or: promote references to a first-class Entry field (like sources/links) rather than leaving it as an ad-hoc frontmatter-only convention that index.py has to fish for after the fact.

Option 2 is probably the more correct fix long-term — references is already treated as structurally significant (creates DB link rows), so it arguably belongs alongside links/sources as a typed field rather than living only in raw frontmatter dicts.

## Acceptance criteria

- A references: key in an EventEntry's (or any core type's) frontmatter survives from_frontmatter -> to_frontmatter round-trip.
- storage/index.py's references extraction (now warning-logged on failure per fail-open-exception-sweep site #4) succeeds for typed entries in the common case, not just GenericEntry.
- Regression test: write an EventEntry (or PersonEntry) markdown file with references:, index it, assert the cross-KB link appears in get_outlinks — parallel to the existing test_references_field_creates_cross_kb_links but for a typed entry instead of a generic/note type.

## Related

- [[fail-open-exception-sweep]] site #4 — the swallowed-exception symptom this gap causes
