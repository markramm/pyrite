---
type: adr
title: "Entry Protocol Mixins"
adr_number: 17
status: accepted
deciders: ["markr"]
date: "2026-03-03"
tags: [architecture, protocols, type-system, mixins]
links:
  - target: "0014-structural-protocols-for-extension-types"
    relation: "refines"
    note: "Concrete implementation of ADR-0014's abstract protocol vision"
---

# ADR-0017: Entry Protocol Mixins

## Context

ADR-0014 established the rationale for structural protocols in Pyrite's extension system. Six extensions independently reinvent the same field patterns: `assignee`, `status`, `priority`, `due_date`, `location`, `date`. This duplication prevents cross-type queries ("all overdue items regardless of type"), complicates DB indexing, and means user-defined types in kb.yaml cannot opt into standardized fields.

Before plugin extraction (milestone 0.17+), we need concrete protocol definitions that extensions compose rather than duplicate.

## Decision

Implement 5 protocol mixins as Python dataclass mixins in `pyrite/models/protocols.py`:

| Protocol | Fields | Purpose |
|----------|--------|---------|
| **Assignable** | `assignee`, `assigned_at` | Entries assigned to people/agents |
| **Temporal** | `date`, `start_date`, `end_date`, `due_date` | Entries with time dimensions |
| **Locatable** | `location`, `coordinates` | Entries with geographic context |
| **Statusable** | `status` | Entries with workflow state |
| **Prioritizable** | `priority` | Entries with priority ranking |

### Not a protocol: Categorizable

Classification vocabulary (capture lanes, review statuses, backlog kinds) is always domain-specific. These stay as FieldSchema `select`/`multi-select` fields defined per-extension or per-kb.yaml.

### Mixin design

Each protocol is a `@dataclass` with:
- Fields with sensible defaults (empty string, 0)
- `_<protocol>_to_frontmatter()` — returns dict of non-default fields
- `_<protocol>_from_frontmatter(meta)` — extracts fields from frontmatter dict

Naming uses underscore-prefixed instance methods to avoid collisions between protocols and with Entry's own `to_frontmatter()`/`from_frontmatter()`.

### Importance promotion

`importance: int = 5` is promoted from 5 independent core types to the base `Entry` class, with `_base_frontmatter()` handling serialization.

### DB column promotion

Protocol fields get dedicated indexed columns in the entry table:
- `assignee TEXT`, `assigned_at TEXT` (new)
- `priority INTEGER` (new)
- `due_date TEXT`, `start_date TEXT`, `end_date TEXT` (new)
- `coordinates TEXT` (new)
- Existing: `date`, `status`, `location`, `importance`

### User-defined type integration

`TypeSchema` gains a `protocols: list[str]` field. When a user-defined type in kb.yaml declares protocols, GenericEntry gains those fields automatically:

```yaml
types:
  meeting:
    protocols: [temporal, locatable, assignable]
    fields:
      agenda: { type: text }
```

### Plugin protocol extension

`PyritePlugin` gains `get_protocols() -> dict[str, type]`. Plugins can define additional protocols beyond the core 5. The registry aggregates them.

## Consequences

- Cross-type queries become possible: "find all overdue assignable entries"
- Extensions compose protocols instead of reinventing fields
- User-defined types can opt into standardized behavior
- DB indexing is consistent across all types using a protocol
- Migration path: extensions gradually adopt mixins, old frontmatter still loads via backward-compatible parsing
