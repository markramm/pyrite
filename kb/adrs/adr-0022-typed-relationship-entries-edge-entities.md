---
id: adr-0022
title: 'ADR-0022: Typed Relationship Entries (Edge-Entities)'
type: adr
adr_number: 22
status: accepted
date: '2026-03-09'
tags:
- core
- graph
- relationships
- schema
- architecture
links:
- target: typed-relationship-entries-as-first-class-entities
  relation: informs
  kb: pyrite
- target: design-journalism-investigation-plugin
  relation: informed_by
  kb: pyrite
---

## Context

Pyrite models relationships as untyped `{target, relation}` pairs in YAML frontmatter `links` arrays. This is sufficient for simple references but cannot represent relationships that carry their own data — an ownership stake with percentage and dates, a board membership with role and term, a funding flow with amount and mechanism.

The journalism-investigation plugin (informed by OCCRP's FollowTheMoney data model) requires relationships to be first-class entries. FtM calls these "edge-entities": an Ownership entry connects an owner to an asset and carries properties (percentage, legal basis, dates). This pattern applies beyond journalism — any KB modeling real-world relationships benefits from typed edges with properties.

Three design questions needed resolution:

1. Where are auto-generated backlinks stored — frontmatter, index, or metadata?
2. Are partial edges (one endpoint missing) allowed?
3. How do edge-entity backlinks interact with existing links and wikilinks?

## Decision

### Edge types in schema

A plugin can declare an entry type as an **edge type** by specifying two distinguished endpoint fields in the schema. The schema declares which fields are endpoints and what entry types they accept.

```yaml
# In kb.yaml or plugin type registration
types:
  ownership:
    edge_type: true
    endpoints:
      source: owner      # field name on the entry
      target: asset       # field name on the entry
    fields:
      owner:
        type: ref
        required: true
      asset:
        type: ref
        required: true
      percentage:
        type: number
      start_date:
        type: date
      end_date:
        type: date
      legal_basis:
        type: string
      beneficial:
        type: boolean
```

### Storage: index-only (no cascading writes)

Auto-generated backlinks from edge-entities are stored **in the index only**, not in endpoint entries' frontmatter.

**Rationale:**
- Consistent with how wikilink backlinks already work — parsed on index, not stored in frontmatter
- No cascading writes: saving an ownership entry does not modify the owner or asset entries
- No circular save dependencies or conflict risks
- `pyrite index sync` rebuilds all edge-derived backlinks, same as wikilinks
- The edge-entity's own frontmatter is the source of truth (`owner: [[putin]]`, `asset: [[company-x]]`)

**Rejected alternative: frontmatter storage.** Saving an edge-entity would require modifying both endpoint entries' frontmatter (adding links), creating cascading writes. Deleting the edge would require modifying them again. This is fragile, conflict-prone in concurrent agent scenarios, and unnecessary given that the index already handles wikilink-derived backlinks the same way.

**Rejected alternative: JSON metadata column.** This is functionally equivalent to index-only but in a separate column. Adds complexity without benefit — the index already has the infrastructure for relationship storage.

### Both endpoints required

Edge-entity entries **require both endpoint fields** at save time, enforced by schema validation.

**Rationale:**
- "Ownership of ?" is meaningless — if you don't know the asset, you don't have an ownership relationship
- "? owns Company X" is equally incomplete — if you don't know the owner, you have a research question, not a relationship
- Provisional or uncertain relationships should be modeled as **claims** (`"Company X has an unknown beneficial owner"`) not as edge-entities. Claims are designed to be provisional; edge-entities are structural assertions.

### Merged backlinks output, labeled by source type

`pyrite backlinks <entity-id>` returns a unified list from three sources, each labeled:

```
$ pyrite backlinks company-x
  ownership-putin-company-x  (edge: ownership.asset)    # edge-entity endpoint
  event-sanctions-2022       (link: relates_to)          # manual frontmatter link
  article-offshore-networks  (wikilink)                  # body wikilink
```

**Rationale:**
- One unified backlinks query — no separate namespaces to search
- Source type labels tell the consumer the structural role of each backlink
- `edge: ownership.asset` means "this entry is an ownership edge-entity and company-x is its asset endpoint" — richer than just "something links here"
- Filters can select by source type: `--type=edge` to see only relationship entries

## Consequences

### Positive
- Plugins can define rich relationship types with arbitrary properties
- Graph queries traverse edge-entities to discover multi-hop connections (ownership chains, money flows)
- No cascading writes — edge-entities are self-contained, consistent with Pyrite's file-based architecture
- Backlinks output is richer and more useful with source type labels
- Claims and edge-entities have clear semantic separation (provisional vs structural)

### Negative
- Edge-derived backlinks require index sync to be current (same as wikilinks — acceptable)
- Schema complexity increases: `edge_type`, `endpoints`, and endpoint validation are new concepts
- Plugins must understand the edge-type protocol to define connection types

### Neutral
- Existing links and wikilinks continue to work unchanged
- No migration needed for existing KBs — edge types are additive
- Graph service needs enhancement to traverse edge-entities (new query patterns)

## Implementation Notes

- Add `edge_type` and `endpoints` to `TypeSchema` in `pyrite/schema/`
- Add an `EdgeType` protocol mixin in `pyrite/models/` declaring endpoint fields
- Index pipeline extracts endpoint fields from edge-type entries and stores as queryable relationships
- `graph_service.py` traverses edge-entities for network queries
- Backlinks query merges three sources: manual links, wikilinks, edge endpoints — each labeled
- Schema validation rejects edge-type entries with missing endpoints
