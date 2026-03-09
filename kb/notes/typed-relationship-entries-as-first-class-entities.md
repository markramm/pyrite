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
links:
- target: vladimir-putin
  relation: owner_of
  kb: timeline
- target: company-x
  relation: asset_in
  kb: timeline
---

Putin holds a 51% beneficial ownership stake in Company X through a Cyprus-registered nominee structure, documented in the Panama Papers leak (2016).
```

## What Core Needs to Support

### 1. Entry types that represent relationships
- An entry type can declare itself as a "connection" or "edge" type
- Edge types have two distinguished fields (e.g., `owner` + `asset`, `person` + `organization`) that identify the endpoints
- These fields accept wikilinks or entry IDs

### 2. Auto-generated bidirectional links
- When an edge-entity is saved, the system automatically maintains backlinks on both endpoint entries
- Deleting the edge-entity removes the auto-generated links
- This is distinct from manual `links` in frontmatter — auto-links are derived, not authored

### 3. Graph traversal through edge-entities
- `pyrite backlinks <entity-id>` should include edge-entities connecting to that entity
- Graph service should traverse edge-entities to build network views
- Query: "find all ownership entries where owner = X" should be efficient (indexed)

### 4. Schema support for edge types
- `kb.yaml` type definitions should support declaring a type as an edge type
- Edge type schema specifies the two endpoint fields and their expected types
- Validators ensure endpoint fields reference valid entries

## What Core Does NOT Need

- Core doesn't need to know about ownership/membership/funding specifically — those are plugin types
- Core provides the infrastructure (edge-type declaration, auto-linking, graph traversal)
- Plugins define the specific edge types and their fields

## Impacted Files

- `pyrite/schema/` — add edge-type support to KBSchema and TypeSchema
- `pyrite/models/` — protocol or mixin for edge-type entries (endpoint field declaration)
- `pyrite/services/kb_service.py` — auto-link maintenance on save/delete of edge entries
- `pyrite/storage/database.py` / `queries.py` — index edge endpoints for efficient querying
- `pyrite/services/graph_service.py` — traverse edge-entities in network queries

## Design Decisions (resolved in ADR-0022)

1. **Index-only storage** — auto-generated backlinks stored in the index, not in endpoint entries' frontmatter. Consistent with how wikilink backlinks work. No cascading writes. Rebuilt by `pyrite index sync`.
2. **Both endpoints required** — enforced by schema validation. Provisional or uncertain relationships should be modeled as claims, not edge-entities. "Ownership of ?" is meaningless; if you don't know the asset, you don't have an ownership relationship, you have a research question.
3. **Merged backlinks, labeled by source type** — `pyrite backlinks` returns unified results from three sources (edge endpoints, manual links, wikilinks), each labeled with its source type (e.g., `edge: ownership.asset`). One query, no separate namespaces.

## Acceptance Criteria

- A plugin can declare an entry type as an edge type with two endpoint fields
- Saving an edge-entity creates index-based backlinks on both endpoints (no frontmatter modification)
- `pyrite backlinks <entity-id>` includes edge-entities, labeled with `edge:` source type
- Graph service traverses edge-entities to build network views
- `pyrite index sync` rebuilds all edge-derived backlinks
- Schema validation rejects edge-type entries with missing endpoints
- At least one plugin (journalism-investigation) uses this for ownership/membership/funding types
