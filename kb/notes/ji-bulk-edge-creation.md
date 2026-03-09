---
id: ji-bulk-edge-creation
title: Bulk edge-entity creation for migrations and batch operations
type: backlog_item
tags:
- journalism
- investigation
- graph
- migration
- performance
links:
- target: ji-connection-entry-types
  relation: depends_on
  kb: pyrite
- target: typed-relationship-entries-as-first-class-entities
  relation: depends_on
  kb: pyrite
kind: feature
status: proposed
priority: medium
effort: S
---

## Problem

Migrating existing data (e.g., 1,235 actors from the kleptocracy timeline) requires creating hundreds of edge-entities. One-at-a-time MCP tool calls are slow — each call validates, saves, and indexes individually. Similar to `task_decompose` for tasks, the system needs a bulk creation path.

## Scope

- MCP tool: `investigation_create_connections` — batch create edge-entities
- Input: array of connection definitions (type, endpoints, properties)
- Validates all entries before creating any (atomic: all succeed or all fail)
- Creates all entries, indexes once at the end (not per-entry)
- Returns: summary of created entries, any validation failures
- CLI equivalent: `pyrite investigation bulk-create-edges --file=connections.yaml`
- YAML/JSON input format for CLI

### Input Format

```yaml
connections:
  - type: membership
    person: person-a
    organization: org-x
    role: CEO
    start_date: 2015-01-01
  - type: membership
    person: person-b
    organization: org-x
    role: CFO
    start_date: 2018-06-15
  - type: ownership
    owner: org-x
    asset: subsidiary-y
    percentage: 100
```

## Acceptance Criteria

- Batch of 100+ edge-entities created in <10s
- Atomic: validation failures reported before any entries are created
- Single index sync at the end (not per-entry)
- MCP and CLI interfaces both work
- Dry-run mode: validate and report without creating
