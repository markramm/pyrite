---
id: adr-0026
type: adr
title: "FIPS and State as Promoted Entry Columns"
adr_number: 26
status: accepted
deciders: ["markr"]
date: "2026-04-10"
tags: [schema, search, geographic, fips]
---

# ADR-0026: FIPS and State as Promoted Entry Columns

## Context

The detention-pipeline-research and igsa-holders KBs both use county FIPS codes as their primary join key for cross-referencing warehouse candidates against IGSA detention facilities. Currently, `fips` and `state` are stored as metadata fields in entry frontmatter. This means:

- They end up in the JSON `metadata` column in SQLite, which is not indexed
- Cross-KB queries require extracting FIPS from JSON, or a bespoke external script
- There is no way to filter search results by FIPS or state

The pattern for promoting frequently-queried metadata fields to indexed DB columns is well-established: ADR-0017 did exactly this for protocol fields like `assignee`, `coordinates`, `due_date`, etc.

## Decision

Add `fips TEXT` and `state TEXT` as columns on the `entry` table, with indexes on both. Thread `fips` and `state` as filter parameters through the full search stack:

- `SearchBackend` protocol
- `SQLiteBackend.search()` and `PostgresBackend.search()`
- `OverlayBackend.search()`
- `QueryMixin.search()`
- `SearchService.search()`
- MCP `kb_search` tool schema
- CLI `pyrite search --fips --state`

During indexing, `fips` and `state` are promoted from entry metadata to the DB columns. KBs that don't use these fields are unaffected (columns remain NULL).

## Consequences

### Positive

- Cross-KB FIPS queries become a single search call: `kb_search query="warehouse" fips="12086"`
- The county-level join between detention-pipeline-research and igsa-holders no longer requires external scripts
- State filtering enables regional analysis across all KBs
- Follows the established pattern from ADR-0017; no new abstractions needed

### Negative

- Two more columns on the entry table (minimal storage cost)
- These are US-specific geographic codes; international KBs would need different fields

### Migration

- Alembic migration 006 adds the columns and indexes
- Existing entries get populated on next reindex (`pyrite index --all`)
- No schema version bump needed; these are optional metadata columns, not protocol fields
