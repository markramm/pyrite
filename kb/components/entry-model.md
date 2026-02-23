---
type: component
title: "Entry Model"
kind: module
path: "pyrite/models/"
owner: "markr"
dependencies: ["pyrite.schema"]
tags: [core, data-model]
---

The entry model defines the base data classes for all knowledge entries.

## Key Files
- `base.py` — Entry base dataclass (id, title, body, summary, tags, sources, links, provenance, metadata)
- `core_types.py` — 8 built-in types: NoteEntry, PersonEntry, OrganizationEntry, EventEntry, DocumentEntry, TopicEntry, RelationshipEntry, TimelineEntry
- `generic.py` — GenericEntry fallback for unknown types

## Type Resolution
`get_entry_class(type_name)` checks core registry, then plugin registry, then falls back to GenericEntry. `entry_from_frontmatter(meta, body)` auto-detects and instantiates.

## Extension Pattern
Plugin entry types extend NoteEntry or DocumentEntry. Must override `from_frontmatter()` to map custom fields. `to_frontmatter()` should call super and set `meta["type"]`.
