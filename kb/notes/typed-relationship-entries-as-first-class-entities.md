---
id: typed-relationship-entries-as-first-class-entities
title: Support typed relationship entries (edge-entities) in Pyrite core
type: backlog_item
tags:
- core
- graph
- relationships
- schema
- plugin-driven
links:
- target: design-journalism-investigation-plugin
  relation: informed_by
  kb: pyrite
- target: adr-0022
  relation: informed_by
  kb: pyrite
- target: ji-connection-entry-types
  relation: blocks
  kb: pyrite
kind: feature
status: proposed
priority: high
effort: L
---

## Problem

Pyrite models relationships as untyped `{target, relation}` pairs in YAML frontmatter links arrays. This works for simple references ("A relates to B") but cannot represent relationships that carry their own data:

- An ownership stake has: owner, asset, percentage, start_date, end_date, legal_basis, beneficial flag
- A board membership has: person, organization, role, term dates
- A funding relationship has: source, recipient, amount, currency, mechanism

The journalism-investigation plugin needs these as first-class entries — the FtM "edge-entity" pattern. An ownership entry is a full KB entry (with its own ID, body, sources, and metadata) that happens to represent a relationship between two other entries.

This is not a journalism-specific need. Any KB modeling real-world relationships hits this: software-kb could use it for dependency relationships with version constraints, intellectual-biography for mentorship relationships with time periods, etc.

## Current State

```yaml
# Current: untyped link, no properties
links:
- target: company-x
  relation: owns
  kb: timeline
```

## Target State

```yaml
# Relationship entry: full entry representing the edge
---
id: ownership-putin-company-x
type: ownership
title: "Putin ownership stake in Company X"
owner: "[[vladimir-putin]]"
asset: "[[company-x]]"
percentage: 51
start_date: 2005-03-15
end_date: null
legal_basis: "Nominee shareholder via Cyprus holding"
beneficial: true
sources:
- "[[panama-papers-doc-4427]]"
---

Putin holds a 51% beneficial ownership stake in Company X through a
Cyprus-registered nominee structure, documented in the Panama Papers leak (2016).
```

Note: no manual `links` array needed — the system derives backlinks from the endpoint fields (`owner`, `asset`) automatically during indexing.

## What Core Needs to Support

### 1. Edge type declaration in schema
- An entry type can declare itself as an edge type with `edge_type: true`
- Minimum two endpoint fields (`source` and `target` roles), no maximum
- Each endpoint declares which field it maps to and which entry types it accepts
- `accepts` constraints prevent nonsensical edges (person owns a timeline event)

### 2. Index-based backlinks (no cascading writes)
- Index pipeline extracts endpoint fields from edge-type entries
- Stores in dedicated `edge_endpoints` table for fast bidirectional queries
- No modification to endpoint entries' frontmatter on save or delete
- `pyrite index sync` rebuilds all edge-derived backlinks
- Consistent with how wikilink backlinks already work

### 3. Graph traversal through edge-entities
- `pyrite backlinks <entity-id>` includes edge-entities, labeled with `edge:` source type
- Merged output from three sources: `edge:`, `link:`, `wikilink:` — one query, no separate namespaces
- Graph service traverses edge-entities to build network views
- Query: "find all ownership entries where owner = X" via `edge_endpoints` table

### 4. Endpoint validation
- All declared endpoint fields required at save time
- Endpoint type constraints validated against `accepts` list
- Broken endpoint references (deleted endpoint entry) handled as QA warning, no auto-deletion — consistent with broken wikilinks
- QA validation flags: "Edge-entity X references nonexistent entry Y"

### 5. Agent discoverability
- MCP tool or query to list available edge types with their schemas
- Returns endpoint constraints, required fields, accepted types
- Enables agents to discover what connection types a KB supports

## What Core Does NOT Need

- Core doesn't need to know about ownership/membership/funding specifically — those are plugin types
- Core provides the infrastructure (edge-type declaration, index table, graph traversal, validation)
- Plugins define the specific edge types and their fields

## Impacted Files

- `pyrite/schema/` — add `edge_type`, `endpoints` (with `accepts`) to TypeSchema
- `pyrite/models/` — protocol or mixin for edge-type entries (endpoint field declaration)
- `pyrite/storage/database.py` — add `edge_endpoints` table
- `pyrite/storage/queries.py` — edge endpoint queries (by endpoint ID, by edge type, bidirectional)
- `pyrite/services/graph_service.py` — traverse edge-entities via `edge_endpoints` for network queries
- `pyrite/services/kb_service.py` — populate `edge_endpoints` on save, validate endpoint types
- `pyrite/cli/` or MCP tools — backlinks output with source type labels

## Design Decisions (resolved in ADR-0022)

1. **Index-only storage** — auto-generated backlinks in the index, not endpoint frontmatter. No cascading writes. Rebuilt by `pyrite index sync`.
2. **All endpoints required** — enforced by schema validation. Provisional relationships are claims, not edges.
3. **Merged backlinks, labeled by source type** — `edge:`, `link:`, `wikilink:` in unified output.
4. **Endpoint type constraints** — `accepts: [person, organization]` prevents nonsensical edges.
5. **Binary default, n-ary allowed** — minimum two endpoints, no maximum.
6. **Broken references = QA warning** — no auto-deletion of edge-entities when endpoint is deleted.
7. **Dedicated `edge_endpoints` table** — fast bidirectional queries by endpoint ID, edge type, or role.

## Acceptance Criteria

- A plugin can declare an entry type as an edge type with endpoint fields and type constraints
- Saving an edge-entity populates `edge_endpoints` table (no frontmatter modification on endpoints)
- `pyrite backlinks <entity-id>` includes edge-entities, labeled with `edge:` source type
- Graph service traverses edge-entities to build network views
- `pyrite index sync` rebuilds all edge-derived backlinks
- Schema validation rejects edge-type entries with missing endpoints or wrong endpoint types
- QA validation flags edge-entities with broken endpoint references
- Available edge types are discoverable via MCP tool or query
- At least one plugin (journalism-investigation) uses this for ownership/membership/funding types
