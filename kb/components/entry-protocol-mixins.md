---
id: protocols-module
title: "Entry Protocol Mixins"
type: component
kind: module
path: "pyrite/models/protocols.py"
owner: core
dependencies:
  - "pyrite/models/base.py"
tags:
  - core
  - architecture
  - protocols
links:
  - target: "0017-entry-protocol-mixins"
    relation: "implements"
---

Composable mixin dataclasses for entry types (ADR-0017). Five protocols:

- **Assignable** — `assignee`, `assigned_at`
- **Temporal** — `date`, `start_date`, `end_date`, `due_date`
- **Locatable** — `location`, `coordinates`
- **Statusable** — `status`
- **Prioritizable** — `priority`

Entry types compose protocols via multiple inheritance (e.g. `class TaskEntry(Assignable, Temporal, Statusable, Prioritizable, NoteEntry)`). Each mixin provides `_<protocol>_to_frontmatter()` and `_<protocol>_from_frontmatter()` helpers.

Exports `PROTOCOL_REGISTRY` (name→class mapping) and `PROTOCOL_FIELDS` (name→field list mapping) for runtime protocol discovery.

Protocol fields are stored in dedicated indexed DB columns (migration v9), enabling cross-type queries via `find_by_assignee()`, `find_overdue()`, `find_by_status()`, `find_by_location()` in `pyrite/storage/queries.py`.
