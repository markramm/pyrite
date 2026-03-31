---
id: entry-model
type: component
title: "Entry Model"
kind: module
path: "pyrite/models/"
owner: "markr"
dependencies: ["pyrite.schema"]
tags: [core, data-model]
---

Entry type hierarchy built on abstract `Entry` dataclass with composable protocol mixins. All entries share invariant fields (id, title, body, tags, links, sources) and implement type-specific serialization. Type dispatch at load time uses `ENTRY_TYPE_REGISTRY` populated by core types and plugin registration.

## Architecture

- `base.py` — abstract `Entry` dataclass with `to_frontmatter()`, `from_frontmatter()`, `to_markdown()`, `from_markdown()`
- `protocols.py` — 6 composable mixin dataclasses: Assignable, Temporal, Locatable, Statusable, Prioritizable, Parentable
- `core_types.py` — 8 concrete types: Note, Person, Organization, Event, Document, Topic, Relationship, Timeline
- `factory.py` — `build_entry()` canonical creation with type resolution and metadata overflow
- `generic.py` — `GenericEntry` fallback for unknown/plugin types
- `collection.py` — `CollectionEntry` for ordered lists/boards
- `task.py` — `TaskEntry` with dependency DAG support

## Type Resolution

```
YAML frontmatter → entry_from_frontmatter() → ENTRY_TYPE_REGISTRY lookup → concrete class
```

Protocol mixins promote fields to DB columns (Assignable → assignee, Temporal → date, etc.) enabling indexed queries on protocol fields.

## Related

- [[entry-factory]] — build_entry() creation path
- [[entry-protocol-mixins]] — composable field groups
- [[kb-repository]] — file I/O using Entry.save()/load()
